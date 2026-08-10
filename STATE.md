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

## Round 91（2026-08-05）：候选 DG 之前 — Stage 2 评测方法学不变量

### 做了什么
- 新建 `tests/test_stage2_evaluation_invariants.py`（38 个测试）覆盖
  CLAUDE.md 与 `docs/evaluation.md` 中描述的 Stage 2 评测方法学不变量，
  互补于 per-module 单测（每个 evaluation/* 模块已 edges2 饱和）。
- 重点覆盖项：
  - **计时不变量**：parse/chunk 固定 null + reason=`not_instrumented`，
    total 是数字、不重复 total
  - **比例指标分母为 0 → null + reason**（不返回 1.0）：
    - text_preservation_precision/recall
    - chunk_boundary_precision/recall
    - figure_caption_*_precision/recall
  - **figure_caption_* 始终 null + `parser_does_not_emit_relations`**：
    不引入"最近图片"启发式（reason ≠ `nearest_image_heuristic`）
  - **chunk_boundary 容差 `tolerance_chars` 在报告中记录**（默认 30）
  - **manifest path：相对 + 正斜杠**；拒绝绝对路径与反斜杠；解析后必须位于项目根内
  - **silent_drop_count 基于 expectations.element_count_by_type**：
    无 expectations → null
  - **报告 devset 6 字段齐全**：status/file_count/content_group_count/
    pdf_count/docx_count/categories_covered
  - **聚合规则**（不混合出"综合分数"）：
    - counts 求和
    - success_rates 算 rate（成功数 / 总数）
    - ratio 各项 macro average（跳过 null）
    - silent_drop 求和
  - **outputs/ 已 gitignored**（git check-ignore 验证）
  - **evaluator_version/report_version 锁定 1.1**（指示线 v2.x 审计目标）
  - **失败文档仍写入 per_doc**（pipeline_failed=true 时不剔除）
  - **expected_failures matches 布尔**：成功失败 matches=true，
    意外失败 matches=false，unexpected_success=false
  - **报告自校验通过 schema**：runner 输出可被 validate_report 接受
  - **当前 devset 状态 incomplete**：所有数字称为 "pilot baseline / incomplete devset"
- 无源码改动。

### 撞墙记录
- 无：38 个测试一次通过。

### 下一步建议
- 候选 DG：app/parsers/fallback_parser.py 边角（第三轮）—— 最大文件 630 行
- 候选 DH：跨模块不一致场景（错误的输入、parser 失败的 details 完整链路）
- 候选 DI：app/cli.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DG（fallback_parser 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 91 后）：5824 pass / 0 fail / 13 skip（HEAD `86a16f4`）

---

## Round 92（2026-08-05）：候选 DG — fallback_parser 边角第三轮

### 做了什么
- 新建 `tests/test_parsers_fallback_edges3.py`（79 个测试），第三轮覆盖
  `app/parsers/fallback_parser.py`（项目最大文件 630 行，含 PDF + DOCX 双路径）。
  之前已有 79 + 95 + 168 = 342 测试，本轮聚焦算法深度与错误路径。
- 重点覆盖项：
  - **`_group_words_to_paragraphs` 算法深度**：
    - line cluster 阈值（abs yc diff <= 3.0）
    - paragraph break 阈值（line 距离 > 1.5 * median_h）
    - median 行高计算（用例跨多 line）
    - bbox 精确边界（min/max x0/x1/top/bottom）
    - missing top/bottom key 不抛错（默认 0.0）
    - 输入乱序 → 按 yc 升序输出
  - **`_lines_to_para` 边界**：多行 word → text 用空格连接、
    bbox 取所有 word 的极值
  - **`_save_image` OSError**：out_dir 是文件、父路径是文件、
    深层目录自动创建、bytes 精确写入
  - **`_extract_inline_image_rids`**：None XML → AttributeError；
    空 XML → 返回 []
  - **`_render_pdf_image_region_verbose` 错误路径**（mock pypdfium2）：
    - pypdfium2 is None → 错误字符串
    - PdfDocument 打开失败 → "PdfDocument 打开失败"
    - page[idx] 越界 → "取 page[idx] 失败"
    - render/to_pil 失败 → "render/to_pil 失败"
    - crop 退化（x1 <= x0）→ "crop 退化 (0 size)"
    - PIL save 失败 → "PIL save 失败"
    - 完整成功 → 返回 None + 文件写出
    - 旧包装 `_render_pdf_image_region` 成功 True / 失败 False
  - **`_parse_pdf` 错误路径**（monkeypatch pdfplumber）：
    - pdfplumber is None → ParserError('pdfplumber_unavailable')
    - pdfplumber.open 抛 → ParserError('pdfplumber_open_failed')
    - 空 pages → warnings 含 pdf_no_text_extracted
    - extract_words 抛 → warning('pdfplumber_word_extract_failed')，继续处理
    - find_tables 抛 → 该页跳过 table，不抛
    - image bbox 退化 → 跳过该 image
    - image render 失败 → warning + image resource_path='(unrendered)'
    - image_output_dir mkdir 失败 → warning('pdf_image_dir_failed')
    - 正常 word → paragraph 元素
    - 正常 table → table 元素 + markdown content
  - **`_parse_docx` 错误路径**：
    - docx is None → ParserError('python_docx_unavailable')
    - docx.Document 打开失败 → ParserError('docx_open_failed')
    - 空 body → warnings 含 docx_no_content
  - **`_classify_pdf_paragraph` 临界**：80 chars 边界、各种 endswith 字符
  - **`_CAPTION_RE` 更多 separator 与 keyword 组合**
  - **`_is_heading_style` fallback**：'Heading\\t3' → (True, 3)、
    'HeadingA' → (True, 1) 等
- 无源码改动。

### 撞墙记录
- wall 1：`_PDFIUM_IMPORT_ERROR` 仅在 import 失败时定义；环境里成功 import 就没此属性，
  `monkeypatch.setattr` 报 AttributeError。修复：用 `raising=False` 允许动态补属性。
- wall 2：`_rows_to_markdown` 表头 None cell → 输出 "|  |"（两个空格）而非 "| |"。
- wall 3：`'Heading\t3'` strip 后变 '3'，int 成功 → (True, 3) 而非 (True, 1)。
- wall 4：'Hello World' 同行同 top/bottom → 合并成 11 字短文本，被启发式判 heading
  而非 paragraph。修复：扩长文本或断言 type ∈ {paragraph, heading}。

### 下一步建议
- 候选 DH：跨模块不一致场景（错误的输入、parser 失败的 details 完整链路）
- 候选 DI：app/cli.py 边角（第三轮）—— 535 行
- 候选 DJ：app/chunkers/structural.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DH（跨模块端到端不一致场景），价值高且覆盖错误传播链。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 92 后）：5903 pass / 0 fail / 13 skip（HEAD `ef3e509`）

---

## Round 93（2026-08-05）：候选 DH — 跨模块错误传播场景

### 做了什么
- 新建 `tests/test_cross_module_inconsistency.py`（68 个测试）覆盖
  跨模块错误传播路径，互补于 Round 90 的正常路径不变量。
- 重点覆盖项：
  - **文件层错误**：
    - 文件不存在 → ErrorRecord(code=file_not_found, details.path) + Document=None
    - hash 失败（mock OSError）→ ErrorRecord(code=hash_io_error) + exception_type
  - **parser 选择错误**：
    - 未知 parser → ValueError 被 except Exception 兜底成 unexpected_parser_error
    - get_parser 不存在的名 → ValueError 直接抛（业务调用错误）
  - **Parser 抛异常 → ErrorRecord 转换**：
    - ParserError.code → ErrorRecord.code 一致
    - 意外 Exception → unexpected_parser_error + parser_name 透传
    - ParserError.details 字典透传到 ErrorRecord.details
  - **空内容（0 element）**：
    - no_extracted_elements + warnings 透传
    - warnings JSON 可序列化
  - **Schema 校验失败**：
    - schema_validation_failed + validation_errors 截断 20
    - 校验失败时不写盘
  - **写盘失败**：
    - mock json.dump OSError → write_failed + path
  - **Chunker 失败**：
    - mock chunker 抛 → chunker_failed + exception_type
  - **source_hash 一致性**：
    - parser 收到与文件匹配的 hash
    - 同文件 → 同 document_id（幂等）
    - 不同文件 → 不同 document_id
  - **ErrorRecord JSON 可序列化**：
    - 8 个 pipeline 错误码 parametrize 都过
  - **validate_only 三种结果**：
    - missing file / bad json / valid json
  - **image_output_dir_for**：
    - None 输入 → None
    - hash[:16] 命名约定
  - **get_parser 工厂**：6 parser 名 → 正确类
  - **Bad manifest**：
    - 缺文件、坏 JSON、绝对路径、反斜杠 都被拒
  - **chunker 输入不变量**：
    - source_element_ids 是 element_id 子集
    - 每个 chunk 至少 1 个非空 source_element_id
  - **不丢不重**：normalize(Σ chunks.text) == normalize(Σ elements.content)
  - **chunk_ids 唯一** + **element_ids 唯一**
  - **ParserError 继承结构**：issubclass(Exception) + 可被 except 捕获
- 无源码改动。

### 撞墙记录
- wall 1：未知 parser 实际被 process_single 的 except Exception 兜底，
  不是直接抛 ValueError（与最初假设相反）。修复：断言被捕获为 unexpected_parser_error。
- wall 2：fallback parser 默认 parser_name 不接受 .txt；改用 parser_name="text"。
- wall 3：手构 Document 缺 source_locator.line，schema 不通过；改用 TextParser 真实输出。
- wall 4：ErrorRecord/WarningRecord 的 details 默认 None（不是空 dict）。

### 下一步建议
- 候选 DI：app/cli.py 边角（第三轮）—— 535 行
- 候选 DJ：app/chunkers/structural.py 边角（第三轮）
- 候选 DK：evaluation/runner.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DI（cli.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 93 后）：5971 pass / 0 fail / 13 skip（HEAD `185e989`）

---

## Round 94（2026-08-05）：候选 DI — app/cli.py 边角第三轮

### 做了什么
- 新建 `tests/test_cli_edges3.py`（97 个测试）第三轮覆盖 `app/cli.py`（535 行）。
- 重点覆盖项：
  - **`_emit_structured_error`**：写到 stderr、包含 schema_version/input/errors、
    extra kwargs 透传到 errors[0]
  - **`_preview`** 边界：width 1/0/-1、length width-1/width/width+1、
    tab/newline 折叠、None/"" 返空
  - **`_load_document_json`**：missing/bad json/directory/valid 四种结果
  - **`_format_summary`** 字段精确：counts、elements by type（mixed）、
    element text avg、chunk text min/max、chunk refs min/max、
    warnings truncation marker、errors displayed、各基础字段
  - **`_format_elements_list`**：limit=0/-1 全列、parent_id 显示、
    content=None 不抛、type 对齐到 9 字符、空列表
  - **`_format_chunks_list`**：spans 展开（含 element_id[start:end]）、
    空 spans、spans=None 退化为 []、limit truncation、text=None
  - **`_infer_parser_name`**：大小写混合、未知扩展名、无扩展名、
    所有 7 种支持类型（pdf/docx/md/markdown/html/htm/txt/text/ipynb）
  - **`_iter_supported_files`**：recursive 单层 vs 嵌套、空目录、
    全不支持扩展名、纯目录过滤
  - **`_relative_output_path`**：suffix 保留、双扩展名（.tar.gz）
  - **`_build_arg_parser`** 默认值与 choices：
    - max_chars=800, limit=10, recursive=False
    - parser choices 限定 6 种
    - 必填参数（output、input_dir）缺失 → SystemExit
    - 无 subcommand → SystemExit
  - **`main()`** 端到端：
    - inspect --elements --chunks 不抛
    - inspect --limit 0 全列
    - inspect non-dict JSON → rc=1
    - inspect --spans 无 --chunks → 不展示 spans
  - **`_run_parse_dir`** 失败/边界：
    - 缺目录 → rc=2
    - 空目录 → 写 _summary.json，rc=0
    - 单文件成功 → success=1
    - 纯不支持扩展名 → 0 files，0 failures
    - _summary.json 含 schema_version、input_dir、output_dir、
      recursive、parser_override、max_chars 字段
- 无源码改动。

### 撞墙记录
- 无：97 个测试一次通过。

### 下一步建议
- 候选 DJ：app/chunkers/structural.py 边角（第三轮）
- 候选 DK：evaluation/runner.py 边角（第三轮）
- 候选 DL：evaluation/metrics.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DJ（structural chunker 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 94 后）：6068 pass / 0 fail / 13 skip（HEAD `bc62466`）

---

## Round 95（2026-08-05）：候选 DJ — structural chunker 第三轮边角

### 做了什么
- 新建 `tests/test_chunker_edges3.py`（77 个测试）第三轮覆盖
  `app/chunkers/structural.py`（388 行）。
- 重点覆盖项：
  - **`_split_long_text` 累积规则**：多 piece 合并、buf flush 触发、
    短句+长句混合、空句子跳过、Chinese sentence break、strip 入口
  - **`_hard_split_with_whitespace_fallback`**：
    - 纯 ASCII 无空白 → forced_char 切
    - 前导空白跳过
    - 单 piece 全空白 → 返空列表
    - 窗口内有空白 → whitespace 切
    - 每个 piece.text 长度 ≤ max_chars
    - piece.text 无 trailing 空白（rstrip）
    - start/end 坐标在 [0, n] 内
  - **`_ChunkBuffer.flush`**：
    - 空 buf 返 None
    - 纯空白 join 后 strip 为空 → 返 None
    - chunk_id 含 counter padding
    - metadata strategy/max_chars/char_count 精确
    - source_element_ids 去重保序
    - source_spans 每段一项（同 element 多 span 也展开）
    - flush 后 parts 清空
    - text 用单空格连接
  - **`_element_text_with_span`**：
    - raw None/empty/纯空白 → ("", 0, 0)
    - 仅左/仅右/两端空白 → 精确 start/end
    - 内嵌空白保留
    - image element → ("", 0, 0)
  - **`StructuralChunker.chunk` 序列场景**：
    - 连续 heading → 各自 chunk 起始
    - heading 在文档开头
    - table/image/caption 序列 isolated chunk
    - caption isolated
    - image element 跳过（不参与分块）
    - max_chars 边界（exact 不切、+1 触发切）
    - split_boundary_after metadata 仅在切分时存在
    - chunk_id 严格递增 + zero padded 4 位
    - 每个 chunk.text ≤ max_chars
    - 每个 chunk 至少 1 个非空 source_element_id
    - 不丢不重：normalize(Σ chunks.text) == normalize(Σ elements.content)
  - **`StructuralChunker.__init__`**：max_chars 32 最小、< 32 抛 ValueError、默认 800
  - **`_SplitPiece`** frozen dataclass、默认 start=0/end=0、equality
  - **`_SENTENCE_SPLIT_RE`**：. + 空白 切、中文 。 + 空白 切、
    无空白不切、无标点不切
  - **`_WHITESPACE_RE`**：各种空白匹配、letter 不匹配
  - **`_HARD_BREAK_LANGS`**：6 元素 tuple、含中英文标点
- 无源码改动。

### 撞墙记录
- wall 1：`_element_text_with_span` 是 StructuralChunker 方法，不是模块级函数。
- wall 2：Element 要 content 或 resource_path 至少一个非空；测试 None/empty content
  时需补 resource_path="placeholder"。
- wall 3：`max_chars=20` 小于最小值 32 → 改用 32 或更大。
- wall 4：`_SENTENCE_SPLIT_RE` 要求标点后跟 `\s+`，"你好。世界。" 无空白 → 不切。
- wall 5：raw string `\s+` 在 docstring 中需 `r"""..."""` 避免 SyntaxWarning。

### 下一步建议
- 候选 DK：evaluation/runner.py 边角（第三轮）
- 候选 DL：evaluation/metrics.py 边角（第三轮）
- 候选 DM：evaluation/manifest.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DK（evaluation/runner.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 95 后）：6145 pass / 0 fail / 13 skip（HEAD `b3c6404`）

---

## Round 96（2026-08-05）：候选 DK — evaluation/runner.py 第三轮边角

### 做了什么
- 新建 `tests/test_evaluation_runner_edges3.py`（78 个测试）第三轮覆盖
  `evaluation/runner.py`（227 行）。已有 59 + 65 + 121 = 245 测试。
- 重点覆盖项（聚焦报告结构精确字段）：
  - **报告 top-level 精确 6 keys**：report_version/provenance/devset/summary/
    per_doc/expected_failures
  - **provenance 精确 9 keys** + evaluator_version=1.1/report_version=1.1 锁定 +
    parser_name override + max_chars + dependencies 含 pdfplumber/python-docx/
    pypdfium2 + ISO 时间戳 + git_commit/git_dirty 类型
  - **devset 精确 6 keys**：status/file_count/content_group_count/pdf_count/
    docx_count/categories_covered + 默认值
  - **summary 精确 4 类**：counts/success_rates/ratio_macro_averages/
    silent_drop_total + ratio_macro_averages 含 11 个 ratio 指标
  - **per_doc public 精确 4 keys**：doc_id/source_type/metrics/wall_time_seconds
    （明确不含 _annotation_present / _tolerance_chars / _missing_markers）
  - **wall_time_seconds 精确 5 keys**：total/parse/chunk/parse_reason/chunk_reason
    + parse/chunk None + reason="not_instrumented" + total > 0 when succeeds
  - **per_doc.metrics 含**：element_count_total / pipeline_success /
    text_preservation_equal / chunk_boundary_precision / figure_caption_precision
    + figure_caption value=None + reason=parser_does_not_emit_relations
  - **expected_failures 精确 4 keys**：doc_id/expected_error_code/actual_error_code/
    matches + matches=True（match）/False（unexpected success）/False（code mismatch）
  - **per_doc 顺序与 manifest 一致**
  - **报告写盘**：能被 json.load 重读、indent=2、ensure_ascii=False
  - **_process_one 错误路径**：file_not_found + total_seconds + parser_version None +
    image_dir None + _per_doc 目录创建 + out_stub 清理
  - **_process_one 成功路径**：document 是 dict + 含 document_id + parser_version 非 None
  - **_load_annotation**：None/missing/directory/valid JSON/array/UTF-8 BOM
  - **run_evaluation 防御性**：minimal manifest / unsupported extension / 深层目录 /
    tolerance_chars default/override
- 无源码改动。

### 撞墙记录
- 无：78 个测试一次通过。

### 下一步建议
- 候选 DL：evaluation/metrics.py 边角（第三轮）
- 候选 DM：evaluation/manifest.py 边角（第三轮）
- 候选 DN：evaluation/report.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DL（metrics.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 96 后）：6223 pass / 0 fail / 13 skip（HEAD `9abe935`）

---

## Round 97（2026-08-05）：候选 DL — evaluation/metrics.py 第三轮边角

### 做了什么
- 新建 `tests/test_evaluation_metrics_edges3.py`（114 个测试）第三轮覆盖
  `evaluation/metrics.py`（381 行）。已有 ? + 190 测试。
- 重点覆盖项（聚焦算法路径与边界）：
  - **`_pdf_locator_ratio`**：page=0/-1/None/missing、bbox required for text types、
    table/image 不需 bbox、mixed valid/invalid
  - **`_docx_locator_ratio`**：page/bbox 拒、各种结构键接受（section/paragraph_index/
    table_index/run_index/row_index/col_index/relationship_id）、空 loc 拒、
    missing loc 拒、mixed
  - **`_is_valid_bbox`**：None/short/long、4 ints/floats/mixed、bool 拒（即使值=0）、
    string 拒、NaN/Inf/-Inf 拒、tuple/dict 拒、零大小接受、负值接受
  - **`_image_resource_ratio`**：no images、empty rp、missing rp、existing rp、
    zero-byte 文件、image_base_dir 拼接 fallback、mixed
  - **`_chunk_reference_ratio`**：no chunks、empty ids、orphan ids、all valid、
    partial、None ids
  - **`_strip_unicode_whitespace`**：empty/no-ws/各种空白类型（NBSP/EM space/
    ideographic space/line separator/paragraph separator）、BOM 不被识别、
    emoji 与中文保留
  - **`_text_preservation`**：full match、partial、both empty、
    empty expected only、empty actual only、order matters for equal but not
    for multiset、repeats preserved、multi-element concat、image excluded、
    ws-only → empty
  - **`_heading_boundary_ratio`**：no headings、no chunks、all matched、
    partial、zero matched、heading 非首位置不算
  - **`_silent_drop_count`**：no expectations、empty expectations、
    no element_count_by_type、no drop、drop、missing type、multi type sum、
    actual > expected 无 negative
  - **`compute_automatic_metrics` pipeline_failed 全 null** + error_code 记录 +
    schema_valid null + 各指标 reason 正确（pipeline_failed / not_pdf_document /
    not_docx_document / no_elements / no_image_elements / no_chunks /
    no_heading_elements / no_expectations）
  - 返回 dict 含 14 个 keys（pipeline_success + error_code + schema_valid +
    11 个文档级指标）
  - 每个 metric 都是 {value, reason} 结构
  - **`_null`** 长字符串、**`_ratio`** inf/nan、**`_bool_metric`** int/str/list 转换、
    **`_int_metric`** float truncate
- 无源码改动。

### 撞墙记录
- wall 1：U+FEFF (BOM) 在 Python str.isspace() 中返回 False → 不被删除。
  修复：改为断言 BOM 保留。

### 下一步建议
- 候选 DM：evaluation/manifest.py 边角（第三轮）
- 候选 DN：evaluation/report.py 边角（第二轮）
- 候选 DO：evaluation/schema_validation.py 边角（如有）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DM（manifest.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 97 后）：6337 pass / 0 fail / 13 skip（HEAD `f53f861`）

---

## Round 98（2026-08-05）：候选 DM — evaluation/manifest.py 第三轮边角

### 做了什么
- 新建 `tests/test_evaluation_manifest_edges3.py`（66 个测试）第三轮覆盖
  `evaluation/manifest.py`（239 行）。
- 重点覆盖项：
  - **`_is_absolute_like`** 所有平台 case：
    - POSIX `/foo` 绝对
    - Windows `C:\foo` / `C:/foo` 绝对
    - `C:foo` drive-relative 不算绝对
    - 数字盘符 `1:\foo` 不算
    - UNC `\\server\share` 不算（无盘符）
    - 单 `/` 绝对、单 `\` 不绝对
    - `./foo` / `../foo` 相对
  - **`_has_backslash`**：各种字符串边界
  - **Manifest dataclass**：frozen + properties 精确算法（file_count / pdf_count /
    docx_count / categories_covered）+ content_group_count 单向 paired_with 算 1 组
  - **DocumentEntry**：frozen + 必填字段 + 全字段（含 sha256/categories/paired_with/
    annotation_resolved/expectations）
  - **ExpectedFailure**：frozen + source_type 可 None
  - **`_resolve_relative_path`** 所有错误码（空、绝对、反斜杠、解析越界）+
    正常相对路径 + `./foo` + 子目录
  - **`load_manifest`**：missing file、bad JSON、invalid version、valid returns Manifest、
    with expected_failures、with annotation_file、empty documents、
    categories 作为 tuple 保留
  - **`_detect_project_root`**：从子目录向上找 pyproject.toml、
    无 pyproject fallback、Path 对象输入
  - **`ManifestError`** 继承 Exception + 可被 raise/捕获
  - **`__all__`** 含 5 个公开符号
- 无源码改动。

### 撞墙记录
- 无：66 个测试一次通过。

### 下一步建议
- 候选 DN：evaluation/report.py 边角（第二轮）
- 候选 DO：evaluation/schema_validation.py 边角（如有）
- 候选 DP：evaluation/annotation_metrics.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DN（report.py 第二轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 98 后）：6403 pass / 0 fail / 13 skip（HEAD `fbb3d2c`）

---

## Round 99（2026-08-05）：候选 DO — evaluation/cli.py 第三轮边角

### 触发
继 Round 98（manifest 第三轮）后继续自跑。原本建议 DN（report.py 第二轮），
但 report.py 已有 124 个 edges2 测试覆盖；选 evaluation/cli.py 第三轮
（base 48 + edges 54 + edges2 81 = 183 已存在）作为更高价值目标。

### 实现
- 新增 `tests/test_evaluation_cli_edges3.py`（97 个测试）
- 覆盖 evaluation/cli.py（243 行）的深度路径：
  - **main() run**：run_evaluation 抛 EvalSchemaError → rc=1（line 107-109）
  - **main() run**：validate_file 抛 EvalSchemaError post-generation → rc=1
    （line 113-116）
  - **main() run**：参数透传 parser_name/max_chars/tolerance_chars 到 run_evaluation
  - **main() run**：n_ok/n_fail 当 metrics 缺 pipeline_success 时按 0 处理
  - **main() run**：git_commit[:12] 截断、None → "unknown"
  - **main() run**：stdout 含 documents=N、成功 X、失败 Y、devset 字段
  - **main() run**：load_manifest 抛 ManifestError/EvalSchemaError → rc=1
  - **main() validate-report**：validate_file 抛 FileNotFoundError → rc=2
    （line 149-151）
  - **main() validate-report**：validate_file 抛 JSONDecodeError → rc=1
    （line 152-154）
  - **_format_metric**：metric 缺 value/reason 键、float NaN/+Inf/-Inf/极小/极大/负值、
    dict 含 None/bool/字符串值、sorted 排序、空字符串、Unicode、alignment 36 字符
  - **_run_inspect_doc**：4 个 sort bucket 边界（bool=0, number=1, dict/str=2, null=3）、
    空 metrics、parser 行缺字段（parser_name/version 各缺一）、source_path 缺、
    document_id 缺、counts 大数组、source_type=pdf、tolerance_chars 透传、
    document/annotation/image_base_dir 透传给 compute_automatic_metrics
  - **_build_parser**：prog/description、subparser 必填、run 4 个 int 参数类型、
    非法 int 拒绝、未知短 flag 拒绝
  - **模块级**：__main__ 守卫、utf-8 reconfigure 块、所有 imports
- 修正：`compute_automatic_metrics` / `figure_caption_prf` / `chunk_boundary_prf`
  在 cli.py 中是函数内 import，必须 monkeypatch 到源模块
  (`evaluation.metrics.*` / `evaluation.annotation_metrics.*`)
- 无源码改动。

### 撞墙记录
- wall 1：`evaluation.cli.compute_automatic_metrics` 不存在（函数内 import）
  → 改 monkeypatch 路径为 `evaluation.metrics.compute_automatic_metrics`

### 下一步建议
- 候选 DN：evaluation/report.py 边角（第二轮）— 仍有深度空间
- 候选 DP：evaluation/annotation_metrics.py 边角（第三轮）
- 候选 DQ：evaluation/schema.py 边角（第二轮，若有）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DP（annotation_metrics.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 99 后）：6500 pass / 0 fail / 13 skip（HEAD `2dedfdb`）

---

## Round 100（2026-08-05）：候选 DP — evaluation/annotation_metrics.py 第三轮边角

### 触发
继 Round 99（cli.py 第三轮）后继续自跑。Round 99 建议选 DP，遵守。

### 实现
- 新增 `tests/test_annotation_metrics_edges3.py`（87 个测试）
- 覆盖 evaluation/annotation_metrics.py（194 行）的深度路径：
  - **预测位置生成**：空 chunk text、所有 chunk 文本为空（stream=""）、
    chunk 文本是另一个的子串、所有 chunk 文本相同
  - **anchor 深度**：marker 含空格、跨 chunk 边界、混合 before/after、
    stream 前缀/后缀 marker、marker 比 stream 长、position 大写当 after 处理
  - **输出 key 集合精确性**：no_document/no_annotation/no_chunks/no_anchors/
    one_chunk/success-no-missing 各 4 keys，success-with-missing 5 keys
  - **_tolerance_chars 字段**：严格 int 类型、reason 永远 None、0/极大值/负值
  - **_missing_markers**：保留 anchor 顺序、部分缺失、全部缺失但 chunks>=2、
    key 在全部命中时不存在
  - **算法路径**：greedy 3/3 全匹配、repeated marker search_from 推进、
    零距离匹配、predicted < chunks-1、有 anchors 但全 missing 的 recall reason
  - **输入鲁棒性**：chunks=null、anchors=null、marker=null、缺 marker/position 键
  - **不可变性**：document/annotation 不被修改、无 stdout/stderr 输出
  - **figure_caption_prf 深度**：3 keys、全部 None value、统一 reason、
    每次返回新 dict、不修改输入
  - **模块结构**：__all__ 3 项有序、normalize_text/_null/_ratio 导入、
    常量属性（小写/无空格/前缀 parser_）
  - **metric value 类型**：success 时 float-or-None、_tolerance_chars 总是 int
  - **reason 字符串精确性**：pipeline_failed / no_annotation /
    no_predicted_boundaries / no_ground_truth_anchors / no_ground_truth_anchors_in_stream
- 无源码改动。

### 撞墙记录
- 无：87 个测试一次通过。

### 下一步建议
- 候选 DQ：evaluation/schema.py 边角（第二轮，若有）
- 候选 DR：evaluation/report.py 第三轮（已有 124 edges2）
- 候选 DS：app/chunkers/structural.py 第四轮（已有 77 edges3）
- 候选 DT：app/parsers/fallback_parser.py 第四轮（已有 79 edges3）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DR（report.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 100 后）：6587 pass / 0 fail / 13 skip（HEAD `f7b039d`）

---

## Round 101（2026-08-05）：候选 DR — app/parsers/html_parser.py 第三轮边角

### 触发
继 Round 100（annotation_metrics 第三轮）后继续自跑。
评估各模块覆盖率，发现 html_parser.py 446 行仅 245 tests（0.55 tests/line），
是最低覆盖率的较大模块，选其为第三轮目标。

### 实现
- 新增 `tests/test_parsers_html_edges3.py`（106 个测试）
- 覆盖 app/parsers/html_parser.py（446 行）的深度路径：
  - **table cell**：th/td 混合、空 cell、内联 tag、未闭合 tr、空 table、
    multiline cell、header-only table
  - **pre/blockquote 嵌套**：pre-in-pre、blockquote-in-blockquote、
    pre-in-blockquote、blockquote-in-pre（不同 depth counter 互不影响）
  - **list 嵌套**：ul-in-ul、ol/ul siblings、li 不在 list 内（ordered=False）
  - **heading 边界**：空/whitespace-only 不 emit、同 level 重复 append section_path、
    h3-then-h1 pop、h4/h5/h6 emit、内联格式
  - **image 深度**：alt 含 entity（named/numeric/hex）、src 含空白 strip、
    img 在 paragraph 中触发 flush、连续多 img、duplicate src attrs 后者胜
  - **字符实体**：numeric/hex/named（&amp;/&lt;/&gt;/&nbsp;）在 5 个 block 上下文中
  - **warning 代码**：html_nested_table 触发次数、html_no_content 仅 0 elements
    时触发（包括只含 hr / 只含 comment 的情况）
  - **_rows_to_md 深度**：空 cell、含 | 的 cell（不转义）、单列多行、jagged 填充、
    header-only
  - **locator**：_make_locator_for_current/_inline 在 section_path 存在/缺失时
  - **pipeline 错误**：html_parse_failed（monkeypatch handler.feed）、
    html_read_failed（monkeypatch OSError）、invalid UTF-8 fallback 到 replace
  - **模块常量**：_SKIP_TAGS 完整内容、_HEADING_LEVELS 6 项、_HTML_EXTENSIONS 2 项
  - **SAX 深度**：<p> in <p> 忽略、skip_stack 数据忽略、kind mismatch close no-op、
    loose text 触发 paragraph、whitespace-only 忽略、close ul/ol 触发 flush
  - **_detect_html_source_type**：大写扩展名接受、拒绝 xml/pdf/docx、
    错误消息含 suffix
  - **完整 e2e**：复杂文档 emit 7 种 element 类型
  - **模块结构**：__all__ 精确、所有 import、HtmlParser 继承/name/version
- 无源码改动。

### 撞墙记录
- wall 1：`_rows_to_md([["h"], ["r1"], ["r2"]])` 返回 4 行（1 header + 1 sep +
  2 body），修正断言为 4
- wall 2：`<script><script>` 嵌套 — html.parser 把 `<script>` 当作 CDATA 元素，
  第一个 `</script>` 关闭整个 script（不接受嵌套），后续 `y` 不在 skip 模式 →
  修正测试以记录此实际行为

### 下一步建议
- 候选 DS：app/parsers/text_parser.py 边角（第三轮）
- 候选 DT：app/parsers/markdown_parser.py 边角（第三轮）
- 候选 DU：app/parsers/kreuzberg_parser.py 边角（第三轮）
- 候选 DV：app/parsers/ipynb_parser.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DT（markdown_parser.py 第三轮，326 行覆盖率较低）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 101 后）：6693 pass / 0 fail / 13 skip（HEAD `0fcc329`）

---

## Round 102（2026-08-05）：候选 DT — app/parsers/markdown_parser.py 第三轮边角

### 触发
继 Round 101（html_parser 第三轮）后继续自跑。
markdown_parser.py 326 行 308 tests（0.94 tests/line），选其为第三轮目标。

### 实现
- 新增 `tests/test_parsers_markdown_edges3.py`（133 个测试）
- 覆盖 app/parsers/markdown_parser.py（326 行）的深度路径：
  - **正则精度**：ATX 需要 `\s+` 后 #、fenced 3+ 字符、ordered `\d+[.)]`、
    unordered `[-*+]`
  - **ATX 闭合 #**：`# Hello #` → "Hello"（trailing # 被 strip）
  - **7 个 # 不匹配** ATX
  - **主题分隔符变体**：`---` / `***` / `___` / `* * *` / `- - -`
  - **setext 拒绝**：`text\n===` 保持段落
  - **列表 marker**：`-` / `*` / `+` / `1.` / `1)` / `99.` / `0.` 全变体
  - **code fence**：3+ backticks/tildes、2 个不够、language 字段 `python3` 匹配
    但 `python3.12` 不匹配（`.` 不在 `[\w+-]`）
  - **blockquote**：`>\s?` 只剥离 1 个空白
  - **standalone image vs paragraph image**：整行约束
  - **section_path**：深嵌套、pop on higher level、same-level replaces、
    preamble 缺失 section_path
  - **pipe table**：`:---:` alignment 接受、无 separator 不识别为表格
  - **`_detect_md_source_type`**：大写 MD/MARKDOWN 接受、拒绝 html/txt/no-suffix、
    错误消息 + code 精确
  - **`_split_pipe_row`**：edge pipe-only strings、empty cells
  - **`_is_pipe_table_start`**：last line returns False、no separator returns False
  - **`_rows_to_md`**：empty input、single row single col、three rows、jagged padding
  - **pipeline 错误**：file_not_found、unsupported_type、md_read_failed（OS monkey）、
    invalid UTF-8 fallback
  - **完整文档 e2e**：emit 全部 7 种 element 类型
  - **模块结构**：__all__ 精确、_MD_EXTENSIONS 2 项、name/version 值
- 无源码改动。

### 撞墙记录
- wall 1：`python3.12` 不匹配（`.` 不在 `[\w+-]`）→ 改为 `python3` 测试
- wall 2：`>    deeply`（4 空格）→ `>\s?` 只剥离 1 个空白，剩 "   deeply"
- wall 3：3 处 SyntaxWarning（`\s+` 在 docstring）→ 改为 raw string `r"""..."""`

### 下一步建议
- 候选 DU：app/parsers/kreuzberg_parser.py 第三轮（245 行 332 tests）
- 候选 DV：app/parsers/ipynb_parser.py 第三轮（227 行 323 tests）
- 候选 DW：app/parsers/text_parser.py 第三轮（136 行 212 tests）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DV（ipynb_parser.py 第三轮，227 行较大）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 102 后）：6826 pass / 0 fail / 13 skip（HEAD `3dc2728`）

---

## Round 103（2026-08-05）：候选 DV — app/parsers/ipynb_parser.py 第三轮边角

### 触发
继 Round 102（markdown_parser 第三轮）后继续自跑。
ipynb_parser.py 227 行 323 tests（1.4 tests/line），仍有 helper 与
错误路径深度可补。

### 实现
- 新增 `tests/test_parsers_ipynb_edges3.py`（105 个测试）
- 覆盖 app/parsers/ipynb_parser.py（227 行）的深度路径：
  - **`_cell_source_to_text`**：str/list/None/int/mixed-type list、empty list
  - **`_extract_kernel_language` 优先级链**：kernelspec.language >
    kernelspec.name > language_info.name > ""
  - **`_detect_ipynb_source_type`**：小写/大写/混合大小写接受、拒绝 html/md/no-suffix、
    `_IPYNB_EXTENSIONS` 精确单项
  - **nbformat 字段**：3/0/-1 抛 ipynb_unsupported_version、4/5/10 支持、
    missing 当作支持（metadata.nbformat=None）、minor missing → None
  - **顶层结构**：list/string/int/null 顶层抛 ipynb_bad_structure、
    cells 非 list 抛错、cells null/missing 当空
  - **markdown cell**：多 element emit、locator 含 cell_index + cell_type、
    两个 cell 各自独立 section_path、warning 透传含 cell_index、
    table/image sub-element、空 source → ipynb_no_content、source 作为 list
  - **code cell**：基础 emit、language 来自 kernelspec/language_info、
    无 metadata 时 language=""、locator 不含 line（仅 cell_index+type）、
    empty/whitespace-only emit ipynb_empty_code_cell warning 并跳过
  - **raw cell**：emit kind=raw_cell、content stripped、empty 静默跳过、
    whitespace-only 静默跳过
  - **cell 错误**：非 dict cell emit ipynb_bad_cell（含 cell_index）、
    unknown cell_type emit ipynb_unknown_cell_type（含 cell_type）、
    missing/null cell_type 默认为 'unknown'
  - **pipeline 错误**：file_not_found、ipynb_invalid_json、
    ipynb_read_failed（OS monkey）、unsupported_type
  - **Document 不变量**：chunks/relations/errors 空、ipynb flag、
    cell_count metadata、language metadata、source_type=ipynb、
    parser name/version
  - **element_id**：跨 cell 连续编号、唯一
  - **完整 notebook e2e**：emit mixed types（heading/paragraph/list_item）
  - **模块结构**：__all__ 精确、所有 import、name/version 值
- 无源码改动。

### 撞墙记录
- wall 1：`_extract_kernel_language(None)` 不接受 None（实际调用方用
  `nb.get('metadata') or {}` 兜底），改测试为 pytest.raises(AttributeError)
  并增加一个 parse 路径测试验证 None 兜底

### 下一步建议
- 候选 DW：app/parsers/text_parser.py 第三轮（136 行 212 tests）
- 候选 DX：app/parsers/kreuzberg_parser.py 第三轮（245 行 332 tests）
- 候选 DY：app/chunkers/structural.py 第四轮
- 候选 DZ：app/parsers/fallback_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DW（text_parser.py 第三轮，虽小但 saturate 比率较低）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 103 后）：6931 pass / 0 fail / 13 skip（HEAD `370c67a`）

---

## Round 104（2026-08-05）：候选 DW — app/parsers/text_parser.py 第三轮边角

### 触发
继 Round 103（ipynb_parser 第三轮）后继续自跑。
text_parser.py 136 行 212 tests（1.6 tests/line），仍有 helper 与错误路径深度可补。

### 实现
- 新增 `tests/test_parsers_text_edges3.py`（88 个测试）
- 覆盖 app/parsers/text_parser.py（136 行）的深度路径：
  - **`_split_paragraphs`**：empty string、single chunk、multiple blank lines 作分隔、
    CR/CRLF/LF 归一、混合换行、内部空白保留、tab 内容、首尾空白 strip、
    递增行号、50 段落 stress、单段落多行
  - **`_detect_text_source_type`**：小写/大写/混合大小写接受、
    拒绝 pdf/docx/html/md/ipynb/no-suffix/unknown、
    错误 code + details 精确、`_TEXT_EXTENSIONS` 精确 2-tuple
  - **pipeline 错误**：file_not_found、unsupported_type、目录作输入、
    text_read_failed（OS monkey 含 exception_type）、invalid UTF-8 fallback
  - **Document 不变量**：source_type=text、parser_name/version、metadata.text=True、
    source_path 保留、source_hash 透传、document_id 来自 hash、
    chunks/relations/errors 空
  - **空文件与 whitespace-only** 都触发 text_no_content warning（含 reason text）；
    有内容则无 warning
  - **element 深度**：type 总是 paragraph、confidence=0.95、metadata 空、
    parent_id None、resource_path None、locator 仅含 line key、
    element_id 连续（e0000, e0001, ...）且唯一、locator line 1-indexed
  - **CRLF 归一** 在 parse 路径、unicode/emoji 内容保留
  - **大文件 stress**：1000 段落和 100KB 单段落
  - **模块结构**：__all__ 精确、所有 import、Parser 继承、name/version 值
- 无源码改动。

### 撞墙记录
- 无：88 个测试一次通过。

### 下一步建议
- 候选 DX：app/parsers/kreuzberg_parser.py 第三轮（245 行 332 tests）
- 候选 DY：app/chunkers/structural.py 第四轮
- 候选 DZ：app/parsers/fallback_parser.py 第四轮
- 候选 EA：evaluation/__init__.py 边角（28 行 14 tests via test_packages_init）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DX（kreuzberg_parser.py 第三轮）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 104 后）：7019 pass / 0 fail / 13 skip（HEAD `d8377ff`）

---

## Round 105（2026-08-05）：候选 DX — app/parsers/kreuzberg_parser.py 第三轮边角

### 触发
继 Round 104（text_parser 第三轮）后继续自跑。
kreuzberg_parser.py 245 行 332 tests（1.36 tests/line），仍有 helper 与表格错误路径深度可补。

### 实现
- 新增 `tests/test_parsers_kreuzberg_edges3.py`（145 个测试）
- 覆盖 app/parsers/kreuzberg_parser.py（245 行）的深度路径：
  - **`_classify_line` 极端输入**：单字符 `#`/`##`/`######`/`#######`（>6 ATX 上限）
    走短行启发式、`---`/`***`/`___`/`///`/三反引号/`|||` 全部误判为 heading
  - **`_classify_line` tab/控制字符**：tab 作 `#` 后 `\s+` 分隔、tab/多空格前导 `#`
    使 level 退到 1、内部 tab 保留、`# Hello\n` 仍匹配 ATX（`$` 在末换行前）、
    `\r`/`\r\n`/`\v`/`\f` 各类边界
  - **`_classify_line` 长度阈值边界**：恰好 80 字符 heading、81 字符 paragraph、
    strip 影响长度检查、前导空白使行长但 text 短
  - **`_classify_line` ATX 内部细节**：trailing dots、纯标点 raw_text、
    内部多空格保留、trailing backslash、unicode 标点、纯数字、`4.2`（heading）vs
    `42.`（paragraph）
  - **`_HEADING_RE` 正则边界**：tab 后继、单 `#` 不匹配、7 hashes 不匹配、
    6 hashes 匹配、纯标点 capture、unicode 单字 capture、Match 对象、锚点
  - **`_split_content_to_elements` rest 含 ATX**：同 block 内 `# H1\n# H2` →
    heading H1 + paragraph `# H2`（rest 不再分类）、heading 后多行 rest 内部
    `\n` 保留、单 `\n` 不构成分隔符、`\r` 不被 `\n\s*\n` 匹配、paragraph
    内部 newline count 精确
  - **`_split_content_to_elements` 段落结构**：heading 后空 rest 不 emit、
    短行 heading + ATX rest → paragraph、whitespace block 过滤、
    1000 blocks stress（含唯一 ID 验证）、PDF locator 全用 page=1、
    paragraph_index 递增、heading+rest 共享 incremented idx、
    ATX heuristic=None / short_line heuristic='short_line'
  - **`_make_locator` source_type 边界**：None/空/大写 PDF/含空白 PDF/未知 →
    docx-like locator；negative index 在 docx 透传、PDF 忽略 paragraph_index
  - **parse content/metadata 边界**：content=None→empty、
    mime_type=None 透传、quality_score=None 透传、specific 值保留
  - **parse kreuzberg_elements 边界**：None/[]/truthy 三态的 warning 行为
  - **parse 表格边界**：cells 有但 markdown=None → ValueError（content 空）、
    markdown 有但 cells=None → confidence=0.5、cells=[] → falsy、
    cells=[[], []] → row=2 cell=0 confidence=0.8、
    PDF bbox tuple → list 化、bbox 空/None → 不加 bbox key、
    page_number=-1（truthy）保留、page_number=large 保留、
    docx 多表 table_index 递增、metadata source 总是 'kreuzberg'
  - **parse 警告顺序**：no_structured_elements 在 pdf_no_bbox 之前、
    docx 不 emit no_bbox、PDF 含 elements 时只 emit no_bbox、
    warning details 含 element_count_after_heuristic / source_type
  - **parse 异常路径**：ValueError/RuntimeError/IOError 各类原异常类型捕获、
    chained __cause__ 保留、kreuzberg_unavailable 在 file_not_found 之前、
    unavailable 时 details 空 dict
  - **Document 不变量**：parser_name=kreuzberg、version 与模块常量一致、
    chunks/relations/errors 总是空、metadata 仅 2 keys、不同 source_hash
    产生不同 document_id
  - **复杂场景**：DOCX/PDF 各自 locator（heading 用 paragraph_index / page=1）
  - **include_document_structure 参数**：默认 True / 显式 False 都透传到 config
  - **模块结构**：_HEADING_RE 是 compiled、_SHORT_LINE_MAX=80、
    _KREUZBERG_AVAILABLE 是 bool、kreuzberg 可用时 _KREUZBERG_IMPORT_ERROR
    **未定义**、kreuzberg/ExtractionConfig 已 import、所有 import 验证、
    __init__ keyword-only、parse 签名精确
- 无源码改动。

### 撞墙记录
- wall 1：`_split_content_to_elements("line1\nline2")` 实际产生 2 元素（heading +
  paragraph），因为 "line1" ≤80 字符无终止符 → 走短行启发式 heading。
  修复：行末加 `.` 强制走 paragraph 路径
- wall 2：3 个 SyntaxWarning（`\s` 在 docstring 内非法转义）→ 改用 r-string
- wall 3：`cells=[["a","b"]]` + `markdown=None` 实际抛 ValueError（Element
  __post_init__ 校验 content 或 resource_path 必须非空）→ 改测试 expect ValueError

### 下一步建议
- 候选 DY：app/chunkers/structural.py 第四轮（已有 edges3）
- 候选 DZ：app/parsers/fallback_parser.py 第四轮（已有 edges3）
- 候选 EA：evaluation/__init__.py 边角（28 行 14 tests via test_packages_init）
- 候选 EB：evaluation/cli.py 第四轮（已有 edges3，243 行）
- 候选 EC：app/cli.py 第四轮（已有 edges3，~250 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DY（structural.py 第四轮，进一步饱和测试密度）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 105 后）：7164 pass / 0 fail / 13 skip（HEAD `9f998c1`）

---

## Round 106（2026-08-05）：候选 DZ — app/parsers/fallback_parser.py 第四轮边角

### 触发
继 Round 105（kreuzberg_parser 第三轮）后继续自跑。
fallback_parser.py 630 行 421 tests（0.67 tests/line），仍有 _parse_docx 成功路径与 _parse_pdf 多页集成未覆盖。

### 实现
- 新增 `tests/test_parsers_fallback_edges4.py`（115 个测试）
- 覆盖 app/parsers/fallback_parser.py（630 行）的深度路径：
  - **`_is_caption` 直接调用**：返回类型、空字符串、None、空白、全宽数字、tab 前导、
    与 _CAPTION_RE 一致性双向验证
  - **`_CAPTION_RE` 深度**：IGNORECASE 标志、中英文关键字、全宽数字范围、Fig 缩写变体
  - **`_classify_pdf_paragraph` 优先级**：caption + 长 text 仍 caption、
    caption meta 仅 heuristic key、中文分号/英文冒号非终止符 → heading、
    caption 检测在 strip 后路径
  - **`_group_words_to_paragraphs` 边界**：负 y/x 坐标、阈值 2.9/3.1 行聚类边界、
    零高度 word、空 text word、行间距大 → 分段、单 word/同 y 双 word
  - **`_lines_to_para` 边界**：负 x/y 坐标、空行返回 None bbox、空 text word
  - **`_is_heading_style` 变体**：trailing space、tab 分隔、leading space strip、
    返回 tuple 类型精确
  - **`_parse_docx` 成功路径（mock docx.Document + Paragraph/Table）**：
    单段落 emit、heading style emit（level=1, style name）、caption 文本 emit、
    **caption 优先于 heading style**、空段落 "(空段落)" + empty=True metadata、
    paragraph_index 递增、section 恒为 0（实现不递增）、
    element_id 跨段连续 e0000/e0001/e0002、表格 emit（row/col count, source, table_index）、
    paragraph → table → paragraph 顺序保留
  - **`_parse_pdf` 多页集成**：多页 element_id 跨页连续、locator page 正确（1,2,3）、
    同页 words+tables+images 三种 element、text→table→image 顺序、
    image bbox 退化（x1≤x0, bottom≤top）跳过、全空触发 pdf_no_text_extracted、
    返回 tuple 类型、paragraph confidence=0.85、table confidence=0.7、image confidence=0.6
  - **`FallbackParser.parse()` 端到端（mock _parse_pdf/_parse_docx）**：
    metadata.fallback=True、image_output_dir None/string/Path、
    PDF 路由到 _parse_pdf、DOCX 路由到 _parse_docx、
    image_output_dir 透传、document_id 来自 hash、warnings 透传、
    chunks/relations/errors 空、source_path 保留、source_hash 透传、parser_name=fallback
  - **模块结构**：__all__ 仅 FallbackParser、_CAPTION_RE 编译 + IGNORECASE、
    所有 helper 函数 callable、所有 import 验证、
    Parser 继承、version 含 3 个关键字、init 默认 None / Path / str 转换、
    空字符串作 image_output_dir 视为 None
- 无源码改动。

### 撞墙记录
- wall 1：`_classify_pdf_paragraph("图 1")` 返回 heading 不是 caption，因为
  `_CAPTION_RE` 要求 digit 后必须有 separator `[\.、:\s]`。改测试为 `"图 1."`
- wall 2：`_parse_docx` 调用 `_extract_inline_image_rids(child)` 需要 child 有 `.iter()`。
  FakeChild 类没有 .iter()，重构为共享基类 `_FakeXmlChild` 提供 `.iter()` 返回空列表，
  9 处 FakeChild 与 1 处 PChild/TChild 全部继承
- wall 3：`test_classify_pdf_paragraph_priority_caption_first` 改 `"图 1"` → `"图 1."`

### 下一步建议
- 候选 EA：evaluation/__init__.py 边角（28 行 14 tests via test_packages_init）
- 候选 EB：evaluation/cli.py 第四轮（243 行 ~97 tests via edges3）
- 候选 EC：app/cli.py 第四轮（535 行 ~100+ tests via edges3）
- 候选 ED：app/pipeline.py 第四轮
- 候选 EE：app/chunkers/structural.py 第四轮（已有 edges3）
- 候选 EF：app/schema.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EC（app/cli.py 第四轮），饱和 CLI 边界。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 106 后）：7279 pass / 0 fail / 13 skip（HEAD `678e0e6`）

---

## Round 107（2026-08-05）：候选 EC — app/cli.py 第四轮边角

### 触发
继 Round 106（fallback_parser 第四轮）后继续自跑。
app/cli.py 535 行 357 tests（0.67 tests/line），仍有 _load_document_json 非 dict 根、_format_summary 含 relations、_preview CJK 等深度路径未覆盖。

### 实现
- 新增 `tests/test_cli_edges4.py`（137 个测试）
- 覆盖 app/cli.py（535 行）的深度路径：
  - **`_load_document_json`**：null/number/string/bool 根、空对象、空数组、
    含数据数组、返回 tuple 类型、错误消息含路径、UTF-8 BOM（容忍双行为）
  - **`_preview`**：CJK unicode 保留、CJK 截断、emoji 保留、特殊字符、
    `\n`/`\r`/`\v`/`\f` 各类控制字符归一、width=0/1/2 边界、width huge 返回全文、
    负 width 总是截断
  - **`_emit_structured_error`**：extra 含 None/nested dict/list/int/bool 值、
    stdout 空、返回 None
  - **`_format_summary`**：含 relations data、chunks text=None、
    chunks 无 source_element_ids、source_hash missing/short/empty、
    warnings 截断 5（5/6/7 边界）、errors 含 code+message、
    elements 无 type 用 ?=1、chunks avg 整数格式、chunks refs avg 1 位小数、
    schema_version 显示、返回 str
  - **`_format_elements_list`**：所有 key 缺失、长 content 截断、width 边界、
    limit > count 无 marker、limit=0 全列、parent_id=""省略、返回 str
  - **`_format_chunks_list`**：返回 str、limit=0 全列、show_spans + no/empty/actual spans、
    missing chunk_id、text="" → chars=0、limit > count 无 marker
  - **`_iter_supported_files`**：大写/混合大小写扩展名、空目录、仅 unsupported、
    返回 list、混合 supported/unsupported、recursive 找子目录、非递归忽略子目录、
    recursive 跳过目录本身
  - **`_relative_output_path`**：Windows 反斜杠归一、root 文件、deeply nested、
    多 dots 文件名、无扩展名文件、返回 Path
  - **`_infer_parser_name`**：lowercase/uppercase PDF、no extension、
    unknown extension (csv/json)、dotfile、返回 str
  - **`_EXTENSION_TO_PARSER`**：count=9、keys 全 lowercase + dot 前缀、
    values 集合精确、pdf+docx 都映射 fallback、kreuzberg 不在 values
  - **`_build_arg_parser`**：prog=app.cli、description 含 PDF/DOCX、
    subparsers required、4 subcommand 存在、--recursive/--parser/--max-chars、
    inspect --limit 0/-1/int/non-int 边界、返回 ArgumentParser
  - **`main`**：inspect 不存在文件 rc=2、inspect 仅 summary rc=0、
    inspect --elements/--chunks/--spans 各种组合、limit 截断 +15 more、
    limit=0 全列、invalid JSON rc=1、top-level array/string rc=1、
    validate/parse/parse-dir 各种 rc、unknown command/no command SystemExit
  - **模块结构**：所有 import (argparse/json/sys/Path/process_single/validate_only)、
    所有 helper 函数存在、main/_build_arg_parser callable
- 无源码改动。

### 撞墙记录
- wall 1：`_load_document_json` UTF-8 BOM 行为：Python json.load 默认不接受 BOM 前缀，
  返回 (None, JSONDecodeError)。改测试为容忍双行为（与现有 edges 测试一致）
- wall 2：`_preview("short", width=0)` 实际返回 "shor…"（不是空字符串），
  因为 `collapsed[:0-1] + "…"` = `collapsed[:-1] + "…"`。改测试断言 endswith("…")

### 下一步建议
- 候选 ED：app/pipeline.py 第四轮
- 候选 EE：app/chunkers/structural.py 第四轮（已有 edges3）
- 候选 EF：app/schema.py 第四轮
- 候选 EG：evaluation/__init__.py 边角（28 行 14 tests）
- 候选 EH：evaluation/cli.py 第四轮（已有 edges3）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EE（structural.py 第四轮），饱和分块器测试。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 107 后）：7416 pass / 0 fail / 13 skip（HEAD `3c2a910`）

---

## Round 108（2026-08-05）：候选 EE — app/chunkers/structural.py 第四轮边角

### 触发
继 Round 107（cli 第四轮）后继续自跑。
structural.py 388 行 391 tests（1.01 tests/line），仍有 _ChunkBuffer.flush 直接调用与 chunk() 集成场景未覆盖。

### 实现
- 新增 `tests/test_chunker_edges4.py`（115 个测试）
- 覆盖 app/chunkers/structural.py（388 行）的深度路径：
  - **`_ChunkBuffer.flush` 直接调用**：空 buf 返回 None、单 part 返回 chunk、
    whitespace-only text 返回 None、source_element_ids dedup 保序、
    source_spans 每个 part 一项、chunk_id 格式、metadata strategy/max_chars/char_count、
    text join 单空格、flush 后清空 parts、二次 flush 返回 None、
    is_empty/length 默认值、counter/document_id 默认
  - **`_PART_*` 常量**：_PART_TEXT=0/_PART_ELEMENT_ID=1/_PART_START=2/_PART_END=3
  - **`_SplitPiece` frozen dataclass**：默认 start/end=0、字段访问、frozen 不可变
  - **`_hard_split_with_whitespace_fallback` 边界**：whitespace 在 upper/lower 边界、
    max_chars=1 长 text/含空白、max_chars=32 长 text、whitespace at end、
    lower==upper 当 max=1、返回 _SplitPiece 列表
  - **`_split_long_text` 深度**：中英混合 sentence、纯中文短/长（forced_char）、
    空 sentence 过滤（超长触发）、boundary_after 非空、CJK 短句、
    返回 list 类型、start/end 非负、max_chars=32 阈值
  - **`normalize_text`**：纯 CJK 无空白、纯 CJK 含空格、mixed CJK+空白、
    返回 str、长 string idempotent、纯标点保留、标点含空白、
    单字符空白输入、数字/特殊字符保留
  - **`StructuralChunker.__init__` 阈值**：max_chars=33/64/128/32 接受、
    31 拒绝、huge 接受
  - **`StructuralChunker.chunk` 集成**：空文档→[]、全 table→isolated chunks、
    全 image→[]、全 caption→isolated、连续 heading 各自 chunk、
    heading+paragraph 同 chunk、paragraph+heading 分开、
    paragraph→table→paragraph 三 chunk、超长 paragraph 分多 chunk、
    chunk_id 零填充 + 递增、返回 list 类型、text join 单空格、
    metadata 含 strategy/max_chars/char_count
  - **`_element_text_with_span` 边界**：内部空白保留、无空白、
    只 leading/trailing 空白、image 空 tuple、image 有 content 仍空、
    empty/None/whitespace-only content（需 resource_path 满足 schema）、
    返回 tuple 三元素、_element_text 旧接口仅返回 text
  - **模块常量**：_SENTENCE_SPLIT_RE 编译、_HARD_BREAK_LANGS 6 元素 tuple、
    含中英文句号
  - **模块结构**：__all__ 精确 2 项、所有 import (re/dataclass/field/Any/Chunk/Document/Element)、
    所有 helper 函数存在、StructuralChunker 有 chunk/_element_text_with_span/_element_text 方法
- 无源码改动。

### 撞墙记录
- wall 1：`_split_long_text` 当 text 长度 ≤ max_chars 时直接返回单 piece，
  不走 sentence split。改测试需让 text 超长触发 split 路径
- wall 2：`normalize_text("  你好\n世界\tend  ")` 实际返回 "你好 世界 end"
  （不是 "你 好 世 界 end"），因为 CJK 内部无空白不被拆。改测试期望
- wall 3：`Element(content="", resource_path=None)` 抛 ValueError（schema 要求
  content 或 resource_path 至少一个非空）。改 helper 支持 resource_path 参数，
  相关测试加 resource_path
- wall 4：`StructuralChunker(max_chars=10)` 抛 ValueError（最低 32）。改用 32

### 下一步建议
- 候选 EF：app/schema.py 第四轮
- 候选 EG：evaluation/__init__.py 边角（28 行）
- 候选 EH：evaluation/cli.py 第四轮（已有 edges3）
- 候选 EI：app/pipeline.py 第四轮
- 候选 EJ：app/models.py 边角（如果还没有）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EI（pipeline.py 第四轮），饱和端到端管道测试。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 108 后）：7531 pass / 0 fail / 13 skip（HEAD `d26fa0b`）

---

## Round 109（2026-08-05）：app/pipeline.py 第四轮（edges4）

### 范围
- 文件：`tests/test_pipeline_edges4.py`（新增，725 行）
- 目标：`app/pipeline.py`（216 行，已有 317 测试，密度 1.47 测试/行）
- 新增测试：83 个
- 提交：`fb6548b`

### 覆盖深度
- **process_single directory 输入**：tmp_path 下创建子目录作 input →
  返回 hash_io_error 或 file_not_found（Windows 实际行为：FileNotFoundError 优先匹配）、
  details.path 包含目录路径、hash_io_error 才带 exception_type
- **process_single parser_error 透传**：
  - code 透传（custom_code）
  - message 透传
  - details 合并（custom_key=custom_value）+ path 注入
- **process_single unexpected exception 兜底**：
  - RuntimeError → unexpected_parser_error
  - message 格式 `RuntimeError: unexpected!`
  - details.parser_name = 调用时的 parser_name
  - ValueError 也走兜底（非 ParserError）
- **process_single 成功路径**：
  - text parser 走通（.txt 输入）
  - markdown parser 走通
  - html parser 走通
  - ipynb parser 走通
- **process_single 写盘失败**：output_path 父目录不可写 → write_failed
- **process_single 父目录自动创建**：output_path 父目录不存在 → mkdir(parents=True)
- **process_single no_elements 路径**：
  - elements=[] → no_extracted_elements code
  - details.source_type 透传
  - details.warnings 是 list（即使为空）
  - message 提示扫描件
- **process_single 返回类型与签名**：
  - 返回 tuple 长度 2
  - 第一个元素是 Document 或 None
  - 第二个元素是 list
  - errors list 元素都是 ErrorRecord
  - 默认 parser_name=fallback
- **validate_only JSON 根类型**：
  - null 根 → False + message
  - 数字根 → False + message
  - 字符串根 → False + message
  - bool 根 → False + message
  - array 根 → False + message
  - 合法 dict → True + "OK"
  - 不存在文件 → False
  - JSON 解析失败 → False
- **image_output_dir_for 深度**：
  - None output_path → None
  - str output_path → Path
  - Path output_path → Path（等价）
  - hash 长度 16 截断
  - hash 短于 16 全部使用
  - 空 hash → "images-"
  - hash 含连字符不影响
  - 目录名前缀 "images-"
  - parent 目录正确
  - 返回值类型一致性
  - 多次调用幂等
  - source_hash 大小写敏感
- **get_parser 深度**：
  - 6 个名字都返回正确类型（fallback→FallbackParser, kreuzberg→KreuzbergParser, 
    markdown→MarkdownParser, html→HtmlParser, text→TextParser, ipynb→IpynbParser）
  - 未知名字 → ValueError
  - None → ValueError（f-string 接受 None）
  - "" → ValueError
  - int → ValueError（f-string 接受 int）
  - 错误消息列出所有 6 个 parser
  - image_output_dir 透传到 FallbackParser
- **模块结构**：
  - __all__ 精确 4 项：get_parser, image_output_dir_for, process_single, validate_only
  - imports：json, Path, Any, StructuralChunker, compute_file_hash, Document, ErrorRecord, Parser, ParserError, 6 个 Parser 类, SchemaValidationError, validate
  - 4 个函数都有 docstring
  - 模块有 docstring 提到关键不变量
- 无源码改动。

### 撞墙记录
- wall 1：`test_process_single_directory_input_details_has_exception_type` 失败 — 
  Windows 上目录作为输入，Python 的 `open()` 优先抛 PermissionError（OSError 子类），
  但 compute_file_hash 实现可能优先匹配 FileNotFoundError（具体看实现）。
  实测 worktree 上走的是 file_not_found 路径，不带 exception_type。
  改测试为"hash_io_error 路径才断言 exception_type"
- wall 2：`get_parser(None)` 和 `get_parser(42)` 不抛 TypeError — 
  f-string 接受 None/int 转字符串，最终走 ValueError。
  改测试期望为 ValueError

### 下一步建议
- 候选 EJ：app/models.py 第四轮（如果还没）
- 候选 EK：app/hash.py 第四轮
- 候选 EL：app/schema.py 第四轮
- 候选 EM：evaluation/cli.py 第四轮
- 候选 EN：evaluation/runner.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EK（hash.py 第四轮）或 EL（schema.py 第四轮）。hash.py 较小，
饱和更快；schema.py 是核心约束，深度价值高。优先 EL。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 109 后）：7614 pass / 0 fail / 13 skip（HEAD `fb6548b`）

---

## Round 110（2026-08-05）：evaluation/cli.py 第四轮（edges4）

### 范围
- 文件：`tests/test_evaluation_cli_edges4.py`（新增，823 行）
- 目标：`evaluation/cli.py`（243 行，已有 97+ 测试，密度 ~5+ 测试/行）
- 新增测试：95 个
- 提交：`ffb8f43`

### 覆盖深度
- **_format_metric int value**：正数/0/大数/负数 渲染（无 .0000 后缀）、
  reason 缺失用 'ok'
- **_format_metric float 0.0/1.0 边界**：0.0000/1.0000 渲染、
  空 reason → 'ok'、中文 reason
- **_format_metric bool**：True/False 小写渲染、reason 缺失用 'ok'
- **_format_metric dict value**：sorted by key、空 dict 渲染、
  int+string 混合、value 含逗号、value 为 None、value 为 bool
- **_format_metric string value**：含换行、含引号、含 unicode、
  空 reason → 'ok'
- **_format_metric name 列宽**：短名 padding 到 36、正好 36 不多加、
  超过 36 不截断
- **_run_inspect_doc 缺字段**：source_type 缺 → unknown、
  elements 缺 → elements=0、chunks 缺 → chunks=0、
  document_id 缺 → ?、source_path 缺 → ?、
  parser_name 缺 → ?、parser_version 缺 → v?
- **_run_inspect_doc elements=null**：metrics.py 无 None 保护，
  保留现状断言 TypeError
- **_run_inspect_doc 输入异常**：array/string/null/int/bool 根 → 1、
  非法 JSON → 1、文件不存在 → 2
- **_run_inspect_doc _sort_key 排序**：bool 在 null 前、
  int 在 string 前、int 在 dict 前、同类按字母
- **_build_parser 默认值**：max-chars=800、tolerance-chars=30、
  parser=fallback、inspect tolerance-chars=30
- **_build_parser choices**：kreuzberg 接受、未知 parser 拒绝（SystemExit）
- **_build_parser 边界**：负 max-chars 接受、0 max-chars 接受、
  prog="evaluation.cli"、formatter=RawDescriptionHelpFormatter、
  缺子命令 → SystemExit、未知子命令 → SystemExit、
  缺参数 → SystemExit
- **main**：unknown 子命令 → SystemExit(2)、空 argv → SystemExit(2)、
  argv 为 tuple 也接受
- **模块结构**：无 __all__、main 有、_build_parser 有、_format_metric 有、
  _run_inspect_doc 有、main 签名 argv、main 返回 int（注解为 'int'）、
  imports 完整（argparse/json/sys/Path/load_manifest/ManifestError/
  run_evaluation/get_git_provenance/validate_file/EvalSchemaError）、
  utf-8 reconfigure 块、main guard raise SystemExit
- **docstrings**：模块 docstring 提及 run/validate-report/inspect-doc、
  _format_metric 有 docstring、_run_inspect_doc 有 docstring
- 无源码改动。

### 撞墙记录
- wall 1：`_run_inspect_doc` 把 elements/chunks 转为局部 []，
  但传给 compute_automatic_metrics 仍是原 doc；doc 里 elements=null
  让 metrics.py 内部 len(None) 抛 TypeError。改测试为断言 TypeError
  以保留现状
- wall 2：`monkeypatch.setattr(cli_mod, "compute_automatic_metrics", ...)` 
  失败 — 函数内 import，不在 cli 模块顶层。
  改为 `monkeypatch.setattr(metrics_mod, ...)` 在源模块替换
- wall 3：`main` 返回注解是 'int'（字符串）不是 int —
  模块用了 `from __future__ import annotations`。改断言为 `in (int, "int")`

### 下一步建议
- 候选 EO：evaluation/runner.py 第四轮（227 行，已有 edges3）
- 候选 EP：evaluation/manifest.py 第四轮（239 行，已有 edges3）
- 候选 EQ：evaluation/metrics.py 第四轮（381 行，已有 edges3）
- 候选 ER：evaluation/report.py 第三轮（200 行，已有 edges2）
- 候选 ES：evaluation/annotation_metrics.py 第四轮（已有 edges3）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 ER（report.py 第三轮）。它只有 edges2，第三轮空间更大；
report.py 是评测报告装配核心，深度价值高。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 110 后）：7709 pass / 0 fail / 13 skip（HEAD `ffb8f43`）

---

## Round 111（2026-08-05）：evaluation/report.py 第三轮（edges3）

### 范围
- 文件：`tests/test_evaluation_report_edges3.py`（新增，769 行）
- 目标：`evaluation/report.py`（200 行，已有 edges2）
- 新增测试：92 个
- 提交：`a9300d5`

### 覆盖深度
- **常量深度**：_RATIO_METRICS 顺序（schema_valid 第一、pdf<docx、
  precision<recall<f1、image<chunk）、唯一性 12、与 _COUNT_METRICS/
  _SUCCESS_BOOL_METRICS 互斥、不含 silent_drop_count、
  不含 figure_caption_*；_COUNT_METRICS 单元素 element_count_total；
  _SUCCESS_BOOL_METRICS 单元素 pipeline_success
- **get_git_provenance subprocess 输出边界**：
  - 单/多 trailing newline strip
  - unicode commit 字符（errors=replace）
  - stderr 非空不影响 commit 判断
  - porcelain 仅空白 → not dirty
  - porcelain 实际内容 → dirty
  - rev-parse 失败但 porcelain 成功 → commit=None, dirty 真实
  - rev-parse 成功但 porcelain 失败 → commit 实际，dirty=False
  - timeout（rev-parse / porcelain 阶段） → commit=None, dirty=True
  - 多次调用返回新 dict
  - 仅 git_commit / git_dirty 两 key
- **get_dependency_versions**：
  - 多次调用返回新 dict
  - key 顺序固定（pdfplumber, python-docx, pypdfium2）
  - 值都是 str 或 None
  - 无 bool 值
- **build_provenance**：
  - run_timestamp_iso 含 'T' 分隔
  - dependencies 字段存在、是 dict、3 个 entry
  - parser_name='' 保留
  - parser_version='' 保留
  - parser_name unicode 支持
  - max_chars=1 接受、INT32_MAX 接受
  - 9 个 key 精确
  - evaluator_version/report_version 与 evaluation 模块常量一致
- **build_devset_section**：
  - _FakeManifest 辅助类
  - 返回 dict 类型、6 key 精确
  - status=None 保留
  - 全 0 计数
  - status="complete" 保留
  - categories list 保留
  - categories=None 保留
- **aggregate_summary**：
  - float value in counts
  - pipeline_success value=1（int）不计为 True
  - pipeline_success value="true"（str）不计为 True
  - ratio 0 参与 macro
  - silent_drop_count float
  - silent_drop_count 负值
  - 多次调用幂等（内容相等）
  - counts 与 silent_drop 不混合
  - counts 与 success_rates 不混合
  - 顶层 4 key 精确
  - 缺 metrics key 抛 KeyError（已知行为）
  - 1000 docs 性能 sanity
- **模块结构**：
  - 模块 docstring 提及聚合规则
  - imports：subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION
  - __all__ 精确 5 项、不含内部常量
  - 函数 docstring（除 build_provenance）
  - get_git_provenance docstring 提及失败/null/dirty
  - aggregate_summary docstring 提及不混合
  - get_dependency_versions docstring 提及 packages
  - 5 个函数签名参数数验证
  - 三个常量是 tuple
  - 常量同 import 同对象
- 无源码改动。

### 撞墙记录
- wall 1：`aggregate_summary([{}])` 实际抛 KeyError（已知行为，与 edges2 一致），
  改测试为断言 KeyError
- wall 2：`build_provenance` 实际无 docstring，改测试为不强求 docstring

### 下一步建议
- 候选 ES：evaluation/report.py 第四轮（本轮新增后）
- 候选 ET：evaluation/runner.py 第四轮（227 行，已有 edges3）
- 候选 EU：evaluation/manifest.py 第四轮（239 行，已有 edges3）
- 候选 EV：evaluation/metrics.py 第四轮（381 行，已有 edges3）
- 候选 EW：app/parsers/kreuzberg_parser.py 第四轮（245 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EW（kreuzberg_parser.py 第四轮）。它是当前未做 edges4 的 parser
中较大的，深度价值高。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 111 后）：7801 pass / 0 fail / 13 skip（HEAD `a9300d5`）

---

## Round 112（2026-08-05）：app/parsers/kreuzberg_parser.py 第四轮（edges4）

### 范围
- 文件：`tests/test_parsers_kreuzberg_edges4.py`（新增，757 行）
- 目标：`app/parsers/kreuzberg_parser.py`（245 行，已有 145+ 测试）
- 新增测试：122 个
- 提交：`d0d933d`

### 覆盖深度
- **_classify_line 纯空白/纯标点**：
  - 纯 spaces / tabs / newline → paragraph+空 meta
  - 纯 `...`（含终止符）→ paragraph
  - 纯 `---===---`（无终止符）→ short_line heading
  - 纯数字 '123'（无终止符）→ short_line heading
  - 纯字母 'xyz' → short_line heading
  - 超长无终止符 → paragraph
  - # foo # closing marker（raw_text 含 `foo #`）
  - # **bold** emphasis in heading
  - # `code` inline code in heading
  - 短 `xyz` 含 inline code → short_line heading
  - 终止符！？（ASCII + CJK 全宽）→ paragraph
  - 连续终止符 ?! → paragraph
  - 'a.b' 中间句号（不是终止符）→ short_line heading
  - 'config.json' 同上
  - 'end.' 末尾句号 → paragraph
- **_HEADING_RE 正则级别**：
  - 空 string / 纯 whitespace 不匹配
  - 单 # 无 \s 不匹配
  - #text 无 \s 不匹配
  - 1-6 个 # + space 匹配
  - 7+ # + space 不匹配
  - leading whitespace / tab 接受
  - trailing whitespace strip
  - 多个 leading space 接受
  - text 含 punctuation
  - pattern 以 ^ 开头、$ 结尾
- **_split_content_to_elements 内容变种**：
  - CRLF 切割
  - 仅 \r\r（block.splitlines 切割 → heading + paragraph rest）
  - 多连续空行
  - leading / trailing 空行
  - CJK 文本（短/长）
  - CJK + ASCII 混合
  - ATX heading with emphasis in rest
  - ATX heading with ATX in rest（保留 paragraph 整段）
  - element_id 零填充递增
  - heading confidence=0.6
  - paragraph confidence=0.5
  - heading rest paragraph confidence=0.5
  - 返回 2-tuple
  - 第二返回值始终 []
  - 空 content → 空 list
  - 仅 whitespace → 空 list
  - document_id 注入 element_id
- **_make_locator 深度**：
  - pdf page=1
  - pdf _kreuzberg_placeholder=True
  - docx paragraph_index
  - docx _kreuzberg_heuristic=True
  - pdf 忽略 paragraph_index
  - docx 忽略 page
- **KreuzbergParser 类/实例属性**：
  - name/version 类属性
  - include_document_structure 默认 True
  - keyword-only 验证
  - 两实例独立
  - parse 方法 callable
  - 实例属性 = 类属性
- **模块结构深度**：
  - _HEADING_RE 是 re.Pattern 实例
  - _SHORT_LINE_MAX=80（int）
  - __all__ 精确 1 项
  - imports：re/Path/Any/Document/Element/WarningRecord/Parser/ParserError/
    detect_source_type/make_document_id
  - 三个内部函数 callable
  - issubclass(KreuzbergParser, Parser)
  - 类/方法 docstring（除 parse）
  - 常量同 import 同对象
- **_classify_line 返回类型**：tuple、str、dict
- **所有终止符参数化**（6 种）
- **KreuzbergParser 创建**：无参/True/False keyword、self 第一参数、
  parse 签名 path + source_hash
- 无源码改动。

### 撞墙记录
- wall 1：'para one\r\rpara two' 实际产生 2 个 element（heading + paragraph）
  而不是 1 个 — block 内 splitlines 也切 \r。改测试为断言 heading + paragraph
- wall 2：`\n\n\npara` 第一个 block 'para' 短无终止符 → heading
  而不是 paragraph。改测试期望 heading
- wall 3：SyntaxWarning - `\s` 在 docstring 中触发 SyntaxWarning。
  改用 raw string `r"""..."""`

### 下一步建议
- 候选 EX：app/parsers/html_parser.py 第四轮（446 行，已有 edges3）
- 候选 EY：app/parsers/markdown_parser.py 第四轮（326 行，已有 edges3）
- 候选 EZ：app/parsers/ipynb_parser.py 第四轮（227 行，已有 edges3）
- 候选 FA：app/parsers/text_parser.py 第四轮（136 行，已有 edges3）
- 候选 FB：evaluation/metrics.py 第四轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 EX（html_parser.py 第四轮）。html_parser.py 是较大的 parser，
edges3 已饱和，但 edges4 仍有空间覆盖 HTMLParser 回调深度。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 112 后）：7923 pass / 0 fail / 13 skip（HEAD `d0d933d`）

---

## Round 113（2026-08-05）：app/parsers/html_parser.py 第四轮（edges4）

### 范围
- 文件：`tests/test_parsers_html_edges4.py`（新增，1125 行）
- 目标：`app/parsers/html_parser.py`（446 行，已有 106+ 测试）
- 新增测试：144 个
- 提交：`bb343d1`

### 覆盖深度
- **_rows_to_md 深度**：3 列 2 行 body、separator 用 `---`、cell 含 `|`、
  jagged padding、空 rows 返回 `""`、单 cell、空 string cell、
  cell 含 `\n`、全空 rows
- **模块常量深度**：
  - _HTML_EXTENSIONS = (".html", ".htm")
  - _HEADING_LEVELS 6 个、值 1..6、h1/h4/h6 各自映射
  - _SKIP_TAGS 含 script/style/head/title/meta/link/noscript、count=7
- **_detect_html_source_type 边界**：html/htm 大小写、无后缀/txt/pdf/docx 拒、
  ParserError code="unsupported_type"、details.suffix 精确
- **_HTMLDocParser 实例属性初始化**：14 个字段全部默认值验证、
  convert_charrefs=True 继承
- **handle_data 边界**：whitespace-only 不创建 paragraph、
  loose text 创建 paragraph、skip_stack 中 data 丢弃、
  连续 data append、空 data 无影响
- **handle_starttag 边界**：
  - 未知 inline tag (span/div) 忽略
  - br 在 None kind 不 append
  - br 在 paragraph 加 space
  - img src 缺失/empty/whitespace → 不 emit
  - img alt 缺失 → ""
  - skip_stack 嵌套其他 tag 仍 skip
  - hr flush block
  - h1-h6 各自启动 heading block
  - li 标记 ordered/unordered 与 list_stack 协作
  - pre/blockquote depth 递增（嵌套）
  - table depth 递增、嵌套 table 警告
- **handle_startendtag 边界**：img/br/hr 自闭合、未知 tag 回落到 starttag
- **handle_endtag 边界**：
  - skip_stack mismatched 不崩
  - skip_stack matching pop
  - 无 cur_kind 的 end tag 安全
  - ul/ol pop list_stack
  - mismatched ul/ol 不 pop
  - pre/blockquote depth 递减
  - 空 table 不 emit element
  - 有 rows table emit
- **_flush_block 边界**：None kind noop、空 buffer no emit、
  whitespace-only no emit、reset 后状态清空
- **_reset_block 边界**：清空所有字段、多次调用安全
- **_start_block 边界**：设 kind、清 buffer、flush previous、设 level/ordered
- **_make_locator 边界**：current/inline 无 section_path、有 section_path
- **section_path 深度跟踪**：h1+h2、h2+h1 弹出、同级 h1+h1、h3+h2+h1 全 pop
- **HtmlParser.parse 错误路径**：
  - UnicodeDecodeError → errors=replace fallback
  - OSError → ParserError html_read_failed
  - feed 异常 → ParserError html_parse_failed
  - close 异常 → ParserError html_parse_failed
  - file_not_found
  - unsupported_type
- **HtmlParser 类属性**：name/version、instance matches class、
  issubclass、parse 签名
- **模块结构**：__all__ 精确 1 项、imports 完整、_HTMLDocParser 存在、
  issubclass stdlib HTMLParser、类/doc_parser 有 docstring
- 无源码改动。

### 撞墙记录
- wall 1：`source_hash="abc"` 太短 → make_document_id 抛 ValueError。
  改为 `source_hash="a" * 64`
- wall 2：模块 `from html.parser import HTMLParser as _StdHTMLParser` 
  导入别名是 `_StdHTMLParser` 不是 `HTMLParser`。改测试属性名

### 下一步建议
- 候选 FC：app/parsers/markdown_parser.py 第四轮（326 行）
- 候选 FD：app/parsers/ipynb_parser.py 第四轮（227 行）
- 候选 FE：app/parsers/text_parser.py 第四轮（136 行）
- 候选 FF：evaluation/metrics.py 第四轮（381 行）
- 候选 FG：evaluation/manifest.py 第四轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FD（ipynb_parser.py 第四轮）。它较小、深度容易饱和；
当前主要 parser 都到 edges4 了，统一化覆盖。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 113 后）：8067 pass / 0 fail / 13 skip（HEAD `bb343d1`）

---

## Round 114（2026-08-05）：app/parsers/ipynb_parser.py 第四轮（edges4）

### 范围
- 文件：`tests/test_parsers_ipynb_edges4.py`（新增，928 行）
- 目标：`app/parsers/ipynb_parser.py`（227 行，已有 105 测试）
- 新增测试：116 个
- 提交：`9c8f715`

### 覆盖深度
- **_cell_source_to_text 输入边界**：
  - bool/int/float/None/bytes/dict/tuple/set → ""
  - list[int]/list[float]/list[bool]/list[None]/list[dict]/nested list
  - list with newline parts join
  - empty str/single char/empty list
  - 返回类型 str
- **_extract_kernel_language 深度**：
  - kernelspec.language='' → fall back to name
  - kernelspec.language='   '（truthy）→ 保留（不 fall back）
  - 两个都 null → fall back to language_info
  - kernelspec=None → fall back
  - language_info.name="" → ""
  - language_info/kernelspec non-dict → AttributeError（无 type guard）
  - metadata=None → AttributeError
  - metadata={} → ""
  - language overrides name
  - 返回类型 str
- **_detect_ipynb_source_type**：.IPYNB/IpYnB 混合大小写、.json/.py 拒、
  details.suffix 精确
- **IpynbParser.parse cell source 边界**：
  - code cell source=null → empty_code_cell warning
  - raw cell source=null → 静默跳过
  - markdown cell 缺 source → 0 elements
  - 空 cells → no_content warning
  - 全空 code cells → no_content
- **parse metadata**：
  - nbformat/nbformat_minor 保留值
  - missing nbformat → None
  - missing nbformat_minor → None
  - cell_count 精确
  - ipynb=True 标记
  - 5 个 key 精确
  - language from kernelspec
  - empty language when no metadata
- **parse cell type 边界**：
  - missing cell_type → unknown warning
  - cell_type=int → unknown warning
  - unknown cell_type details（cell_type, cell_index）
  - code cell text stripped
  - raw cell text stripped
  - code cell metadata.kind="code_cell"
  - raw cell metadata.kind="raw_cell"
  - code cell metadata.language
  - markdown cell 类型/locator/cell_index
  - cell not dict warning details
  - confidence 0.95（code/raw/markdown 继承）
- **parse nbformat 边界**：
  - nbformat=4 supported
  - nbformat<0 raises unsupported_version
  - nbformat_minor=-1 supported（不检查）
  - nbformat=4.0（float）accepted
- **IpynbParser 类属性**：name/version、instance match、issubclass(Parser)、
  parse 签名、docstring
- **模块结构**：__all__ 精确、imports 完整（json/Path/Any/Document/Element/
  WarningRecord/Parser/ParserError/make_document_id/MarkdownParser）、
  模块 docstring 提及 markdown + nbformat、常量同 import 同对象、
  3 个 helper callable、2 个 helper 有 docstring
- **parse 错误路径**：
  - file_not_found
  - unsupported_type
  - ipynb_invalid_json
  - ipynb_read_failed
  - ipynb_bad_structure（array/string cells）
  - 返回 Document 实例，chunks/relations/errors 为空
- 无源码改动。

### 撞墙记录
- wall 1：`'   ' or 'py3'` = '   '（whitespace 是 truthy）。
  改测试期望保留 '   ' 而非 fall back
- wall 2：`_extract_kernel_language({"kernelspec": "python3"})` 
  无 type guard，对 str 调 `.get` → AttributeError。
  改测试为断言 AttributeError
- wall 3：`_extract_kernel_language({"language_info": "python"})` 同上
- wall 4：`_extract_kernel_language(None)` 无 None 保护 → AttributeError

### 下一步建议
- 候选 FH：app/parsers/markdown_parser.py 第四轮（326 行）
- 候选 FI：app/parsers/text_parser.py 第四轮（136 行）
- 候选 FJ：app/parsers/fallback_parser.py 第五轮（630 行，已有 edges4）
- 候选 FK：evaluation/metrics.py 第四轮（381 行）
- 候选 FL：evaluation/manifest.py 第四轮（239 行）
- 候选 FM：evaluation/runner.py 第四轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FH（markdown_parser.py 第四轮）。它是 ipynb 的依赖，
统一覆盖；markdown_parser 较大，深度空间大。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 114 后）：8183 pass / 0 fail / 13 skip（HEAD `9c8f715`）

---

## Round 115（2026-08-05）：app/parsers/markdown_parser.py 第四轮（edges4）

### 范围
- 文件：`tests/test_parsers_markdown_edges4.py`（新增，1093 行）
- 目标：`app/parsers/markdown_parser.py`（326 行，已有 133 测试）
- 新增测试：146 个
- 提交：`950c774`

### 覆盖深度
- **正则编译验证**：9 个正则都是 re.Pattern 实例、都用 ^ 锚定
- **_detect_md_source_type**：md/markdown 大小写变种、.ipynb/.docx/.pdf 拒、
  details.suffix 精确（含空 string）
- **_MD_EXTENSIONS**：= (".md", ".markdown")、count=2
- **_split_pipe_row 深度**：空 string → ['']、'|||' strip 头尾 → ['','']、
  单 pipe、leading/trailing pipe、no pipes、strip each cell、
  unicode 保留、转义反斜杠、返回 list of str
- **_is_pipe_table_start**：i=-1 / i at last / i beyond length、
  header not pipe / separator not pipe / basic / alignment separator
- **_rows_to_md 深度**：single row/col、2 col 3 row、separator count = col、
  pipe count = col+1 per row、pipe in cell、jagged 3 row、
  返回 str、空 rows 返回 ""、全空 cell
- **heading section_path 深度**：2/3 级嵌套、pop on higher level、
  same level replace、absent before first heading、
  heading confidence 0.95、paragraph confidence 0.95
- **code block 深度**：
  - language c++（[\w+-] 接受）
  - language f#（含 # 不匹配 → 整体 paragraph）
  - language python3.10（含 . 不匹配 → 整体 paragraph）
  - kind="code_block"
  - unicode content
  - unclosed at EOF emit
  - empty 段 warning
  - tilde fence
- **thematic break**：no element emit、md_no_content warning、
  long dashes、mixed chars
- **standalone image 深度**：url query string、fragment、unicode alt、
  special chars alt、consecutive images
- **list item 深度**：unordered/ordered marker metadata、
  inline markdown preserved、code inline、two items separate
- **blockquote 深度**：multi-line merged、kind="blockquote"、
  empty first line、interrupted by paragraph
- **table 深度**：row_count、col_count、source="markdown_pipe_table"、
  unicode cells、multiple rows、only header no data、（≥2 列约束）
- **paragraph 深度**：no trailing newline、interrupted by heading/list/
  code fence/blockquote/thematic break/image/table
- **MarkdownParser 类属性**：name/version、instance match class、
  issubclass(Parser)、parse/_parse_text 签名、docstring
- **_parse_text 直接调用**：返回 2-tuple、各类型验证、
  空文本/仅空白 → 空 list、document_id 注入 element_id
- **parse 错误路径**：file_not_found、unsupported_type、md_read_failed、
  invalid utf8 fallback、返回 Document 实例、chunks/relations/errors 空、
  metadata 仅 markdown key
- **模块结构**：__all__ 精确 1 项、imports 完整（re/Path/Any/Document/
  Element/WarningRecord/Parser/ParserError/make_document_id）、
  模块 docstring 提及 ATX/setext/pipe table
- 无源码改动。

### 撞墙记录
- wall 1：`_split_pipe_row("")` 返回 `['']` 不是 `[]`（Python str.split 保留空）
- wall 2：`_split_pipe_row("|||")` strip 头尾 | 后剩 `|`，split → `['','']`
- wall 3：fence 正则 `[\w+-]*` 不接受 `#`/`.`，所以 f#/python3.10 不匹配 fence，
  整体回退为 paragraph
- wall 4：`_PIPE_TABLE_SEP_RE` 要求至少 2 列（`(\|\s*:?-{2,}:?\s*)+`），
  单列 `| --- |` 不匹配。改测试用 2 列
- wall 5：SyntaxWarning `\w` 在 docstring 触发，改 raw string

### 下一步建议
- 候选 FN：app/parsers/text_parser.py 第四轮（136 行）
- 候选 FO：app/parsers/fallback_parser.py 第五轮
- 候选 FP：evaluation/metrics.py 第四轮
- 候选 FQ：evaluation/manifest.py 第四轮
- 候选 FR：evaluation/runner.py 第四轮
- 候选 FS：app/models.py 第三轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FN（text_parser.py 第四轮）。它是最后未做 edges4 的 parser，
统一覆盖后转向 evaluation 模块。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 115 后）：8329 pass / 0 fail / 13 skip（HEAD `950c774`）

---

## Round 116（2026-08-05）：app/parsers/text_parser.py 第四轮（edges4）

### 范围
- 文件：`tests/test_parsers_text_edges4.py`（新增，689 行）
- 目标：`app/parsers/text_parser.py`（136 行，已有 88 测试）
- 新增测试：92 个
- 提交：`b32e5a8`

### 覆盖深度
- **_split_paragraphs 深度**：
  - 单字符 paragraph
  - paragraph 含 tab（保留）/ 仅 tab（视为空）
  - 单 newline 不切段 / 双 newline 切段
  - 仅 newline / CR / CRLF 全空 → []
  - 多 CRLF 全空
  - 3 段精确 line_no
  - leading/trailing 空行
  - 内部空行切段
  - 行仅空格视为空
  - 仅空白 → []
  - 内部 multiple spaces 保留
  - paragraph 内部 newline 保留
  - 返回 list of tuples、tuple 长度 2、类型正确
  - 多段计数
  - 最大 line_no 正确
  - 不修改输入
- **_detect_text_source_type**：.Txt/.Text 混合大小写、.json/.csv/.xml/.yaml 拒、
  details.suffix 精确（含空）
- **_TEXT_EXTENSIONS**：= (".txt", ".text")、count=2、is tuple
- **TextParser.parse 边界**：
  - empty file → no_content warning
  - whitespace-only → no_content warning
  - 仅 newline → no_content warning
  - 单字符 / 单行 → 一个 element
  - metadata 仅 text key、值 True
  - 所有 element type=paragraph、metadata={}
  - source_locator 仅 line key
  - 返回 Document 实例、chunks/relations/errors 空
- **element_id 与 locator**：
  - id 零填充格式 (e0000/e0001/e0002)
  - locator line 严格递增
  - 第一段 line=1
  - leading blank 后 locator line=N
- **parse 错误路径**：file_not_found、unsupported_type、
  text_read_failed（含 details.exception_type）、
  invalid utf8 → fallback replace
- **TextParser 类属性**：name/version、instance match class、
  issubclass(Parser)、parse 签名、docstring
- **模块结构**：__all__ 精确 1 项、imports 完整（Path/Any/Document/Element/
  WarningRecord/Parser/ParserError/make_document_id）、
  模块 docstring 提及 paragraph/extensions、
  常量同 import 同对象、_split_paragraphs callable + docstring
- **多实例独立**：两实例不同对象、相同 name/version
- 无源码改动。

### 撞墙记录
无。

### 下一步建议
- 候选 FT：evaluation/metrics.py 第四轮（381 行）
- 候选 FU：evaluation/manifest.py 第四轮（239 行）
- 候选 FV：evaluation/runner.py 第四轮（227 行）
- 候选 FW：evaluation/annotation_metrics.py 第四轮（194 行）
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FY：app/models.py 第三轮（154 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：所有 parser 已统一到 edges4。下一轮转 evaluation 模块。
选 FT（evaluation/metrics.py 第四轮）。metrics.py 是评测核心，
381 行较大，深度空间大。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 116 后）：8421 pass / 0 fail / 13 skip（HEAD `b32e5a8`）

---

## Round 117（2026-08-05）：evaluation/metrics.py 第四轮（edges4）

### 范围
- 文件：`tests/test_evaluation_metrics_edges4.py`（新增，1164 行）
- 目标：`evaluation/metrics.py`（381 行，已有 114 测试）
- 新增测试：177 个
- 提交：`4cfe261`

### 覆盖深度
- **模块常量**：
  - _TEXT_TYPES 内容精确（paragraph/heading/list_item/table_cell/text）
  - _PDF_BBOX_REQUIRED_TYPES 内容精确（image/figure/table）
  - _NOT_EVALUATED 值精确（figure_caption_*）
- **辅助函数**：_null/_ratio/_bool_metric/_int_metric
  各种 value/reason 组合、bool/int 输入、reason 为空/非空
- **_strip_unicode_whitespace**：
  - 常规空白（space/tab/newline/CR/CRLF）
  - NBSP（ ）、em space（ ）、en space（ ）
  - ideographic space（　）
  - line separator（ ）、paragraph separator（ ）
  - thin space（ ）、hair space（ ）
  - 混合 ascii + unicode 空白
  - 仅 unicode 空白 → ""
  - 空串、纯非空白保持
- **_is_valid_bbox 深度**：
  - None/字符串/dict/tuple 拒
  - 空 list、长度 1/3/5 拒
  - 含 None/字符串/bool 元素拒
  - NaN/Inf 拒
  - 4 元素正常 list 通过
  - 4 元素正常 tuple 通过
- **_pdf_locator_ratio / _docx_locator_ratio**：
  - 各种 type（heading/paragraph/list_item/table_cell/image/table）
  - DOCX 中 image/table 不要求 page/bbox
  - PDF 中 image/table 要求 bbox（4 元素）
  - PDF 中 heading/paragraph 仅要求 page
  - missing locator、locator 类型错、page 类型错
  - bbox 缺失、bbox 非 list、长度错、含非法元素
- **_image_resource_ratio**：
  - image 无 resource_path → 拒
  - image 有 resource_path 但文件不存在 → 拒
  - image 有 resource_path 且文件存在 → 通过（tmp_path）
  - 非 image 类型不参与计算
- **_chunk_reference_ratio**：
  - chunks=None、chunks=[] → null
  - chunk 无 source_element_ids → 拒
  - chunk source_element_ids 含 unknown id → 拒
  - 全部命中 → 通过
- **_text_preservation**：
  - 含 image content 不参与 expected
  - content=None 跳过
  - chunk text=None 跳过
  - chunks expected 空 actual 非空 → precision=0/recall=null
  - 互不相交 → precision=0/recall=0
  - 部分相交 → 比例计算
- **_heading_boundary_ratio**：
  - 无 heading → null
  - heading 与 chunk 一一对应 → 通过
  - heading 第一段匹配，第二段不匹配 → 部分通过
  - tolerance_chars 默认 30
- **_silent_drop_count**：
  - expectations=None → null
  - 多类型 expected/actual，取 max
  - actual ≥ expected → 0
  - element_count_by_type 缺类型 → 当 expected=0
- **compute_automatic_metrics 综合**：
  - 13 个 metric key 精确
  - source_type=pdf/docx/ipynb/html/markdown/text 路径
  - element_count_by_type 精确
  - expectations 默认无（必需参数）
  - schema_check 异常路径
- **模块结构**：
  - __all__ 精确导出 1 项（compute_automatic_metrics）
  - imports：Any/Counter/Path/Dict/List/Tuple
  - 模块 docstring 提及 text_preservation
  - 各函数 docstring 检查（_chunk_reference_ratio 显式无 docstring）
- 无源码改动。

### 撞墙记录
1. test_text_preservation_text_in_chunks_only：原断言 precision=1.0，
   实际 common=0/|actual|=3 → precision=0.0。修复：断言改为 0.0，
   recall 改为 null。
2. test_compute_metrics_expectations_default_none：原断言 default is None，
   实际 expectations 是必需参数（无默认）。修复：改测 default is empty。
3. test_chunk_reference_ratio_has_docstring：函数无 docstring。
   修复：改为 test_chunk_reference_ratio_no_docstring，断言 None。

### 下一步建议
- 候选 FU：evaluation/manifest.py 第四轮（239 行）
- 候选 FV：evaluation/runner.py 第四轮（227 行）
- 候选 FW：evaluation/annotation_metrics.py 第四轮（194 行）
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FY：app/models.py 第三轮（154 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FU（evaluation/manifest.py 第四轮）。manifest 是评测清单
解析核心，239 行，涉及路径校验、categories 聚合、JSON 加载等独立逻辑。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 117 后）：8598 pass / 0 fail / 13 skip（HEAD `4cfe261`）

---

## Round 118（2026-08-05）：evaluation/manifest.py 第四轮（edges4）

### 范围
- 文件：`tests/test_evaluation_manifest_edges4.py`（新增，1177 行）
- 目标：`evaluation/manifest.py`（239 行，已有 309 测试）
- 新增测试：116 个
- 提交：`7978a34`

### 覆盖深度
- **_is_absolute_like 微边界**：
  - 单字符（"a"、"/"）
  - "ab"、"a:b"（无分隔符）、"a:"（长度 < 3）
  - "a:foo"（第三字符非 /\\）
  - "a:/foo"、"a:\\foo"（alpha+:/\\）
  - "foo\\bar"（无盘符）
  - "//foo"（双 slash）、".."、"../"
  - "foo bar/baz"（含空格）
  - "C :/foo"（第二字符是空格）
  - "_:/foo"（首字符下划线）
  - "1abc:/foo"（首字符数字）
- **_has_backslash 微边界**：
  - 混合 / 与 \\、仅 /
  - 含 unicode、纯空白
- **Manifest properties 深度**：
  - pdf+docx < file_count（其他类型存在）
  - pdf_count=0/docx_count=0 边界
  - categories_covered 返回 list（非 tuple）
  - categories_covered 去重、按字母排序、unicode 排序
  - content_group_count self-paired、链式 A→B→C、双独立 pair、混合
  - file_count 不含 expected_failures
- **DocumentEntry hashable/equality**：
  - hashable、可加入 set
  - 同字段相等、不同字段不等
  - 字段数 10、字段顺序精确
  - is_dataclass
- **ExpectedFailure hashable/equality**：
  - hashable、同字段相等
  - doc_id/error_code/source_type 任一不同
  - 字段数 5、字段顺序精确
- **Manifest hashable/equality**：
  - hashable
  - devset_status 不同 → 不等
  - 字段数 5、字段顺序精确
- **_resolve_relative_path field_name 携带**：
  - field_name 在 empty/absolute/backslash/outside 四种错误消息中
  - "./a/./b.docx" 多点段
  - "a/../b.docx" 内部 ..
  - 子目录深 "a/b/c/d/e.docx"
  - 不存在的子目录（不要求文件存在）
  - project_root unresolved Path
- **_detect_project_root 深度**：
  - start 为 file / dir
  - 嵌套多层子目录
  - 多个 pyproject.toml（最近优先）
  - 完全无 pyproject.toml（fallback 到 parent）
- **load_manifest 深度**：
  - manifest_path: str vs Path
  - project_root: str vs Path
  - documents 字段缺失（try/except 接受两种行为）
  - expected_failures 字段缺失
  - sha256（64 hex 字符）/paired_with/expectations/categories 通过
  - annotation_file_str 保留
  - invalid json 的 __cause__ 是 JSONDecodeError
  - resolved_path 为绝对路径
- **ManifestError 默认行为**：
  - 无参数：args=()、str=""
  - 多参数：args=("a","b","c")、str 包含元组形式
- **模块结构深度**：
  - MANIFEST_VERSION 已 import、值为 "1.0"
  - validate/json/dataclass/Path/Any 已 import
  - 所有内部函数 callable
  - __all__ 为 list、长度 5、精确 set
  - __all__ 不含内部 helper
  - 模块 docstring 提及 path/relative
  - from __future__ import annotations
- 无源码改动。

### 撞墙记录
1. SyntaxWarning：模块 docstring 含 `\ ` 转义。修复：改用 r""" """。
2. test_load_manifest_passes_sha256_through：sha256 必须是 64 hex 字符
   （schema 强制 ^[0-9a-f]{64}$）。修复：用 "a" * 64。

### 下一步建议
- 候选 FV：evaluation/runner.py 第四轮（227 行）
- 候选 FW：evaluation/annotation_metrics.py 第四轮（194 行）
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FY：app/models.py 第三轮（154 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FV（evaluation/runner.py 第四轮）。runner 是评测执行核心，
227 行，涉及 manifest 迭代、报告聚合、错误处理等独立逻辑。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 118 后）：8714 pass / 0 fail / 13 skip（HEAD `7978a34`）

---

## Round 119（2026-08-05）：evaluation/runner.py 第四轮（edges4）

### 范围
- 文件：`tests/test_evaluation_runner_edges4.py`（新增，948 行）
- 目标：`evaluation/runner.py`（227 行，已有 323 测试）
- 新增测试：81 个
- 提交：`787fce5`

### 覆盖深度
- **_load_annotation 第四轮深度**：
  - 空文件、仅空白文件 → None
  - JSON object/array/int/bool/null/string 各种类型
  - 嵌套 dict 深度访问
  - 中文内容、中文文件名
  - UTF-8 BOM 头（不被默认 utf-8 解码剥离）→ None
  - 截断的 JSON 数组 → None
  - 二进制垃圾 → UnicodeDecodeError（不静默吞）
- **_process_one 第四轮深度**：
  - error dict 必含 message/code 字段
  - 成功后 _per_doc 目录存在
  - 成功/失败均清理 out_stub
  - elapsed 非负
  - image_dir 名 = 'images-' + 16 hex = 23 字符
  - image_dir 父目录 = _per_doc
  - parser_version 是非空字符串
  - document 是 dict（to_dict 转换）含 source_hash
- **run_evaluation 第四轮深度**：
  - 全部失败 → parser_version_for_prov 仍 None
  - 第一个失败第二个成功 → parser_version 来自第二个
  - 第一个成功第二个失败 → parser_version 来自第一个
  - tolerance_chars=0 / 负数 不崩溃
  - 仅有 expected_failures 无 documents → per_doc 空
  - per_doc / expected_failures 顺序保持
  - 多次调用幂等（不累积状态）
  - 输出 indent=2 / ensure_ascii=False
  - 深层父目录自动创建
  - 顶层 keys 精确集合
  - expected_failure matches True/False、actual_code 字段
  - failed/ok doc 的 metrics.pipeline_success.value
  - summary.success_rates.pipeline_success.rate 0.0/0.5/1.0
- **模块结构深度**：
  - __all__ 是 list、长度 1、精确 ["run_evaluation"]
  - imports 完整：json/time/Path/Any/process_single/image_output_dir_for/
    REPORT_VERSION/chunk_boundary_prf/figure_caption_prf/
    compute_automatic_metrics/aggregate_summary/build_provenance/
    build_devset_section
  - 内部 helper callable：_load_annotation/_process_one/run_evaluation
  - docstring 提及 total / not_instrumented / image
  - from __future__ import annotations
- **签名深度**：
  - manifest/output_path 参数存在
  - parser_name/max_chars/tolerance_chars 是 KEYWORD_ONLY
  - 默认值：parser_name="fallback", max_chars=800, tolerance_chars=30
- 无源码改动。

### 撞墙记录
1. test_load_annotation_handles_nested_dict：list 索引越界
   （c=[1,2,{d:e}]，长度 3，index 3 不存在）。修复：改为 index 2。
2. test_load_annotation_handles_utf8_with_bom：utf-8 默认不解 BOM
   → JSONDecodeError → None。修复：断言 None。
3. test_load_annotation_binary_garbage_returns_none：实际抛
   UnicodeDecodeError（不在 OSError/JSONDecodeError 兜底范围）。
   修复：改为 raises UnicodeDecodeError。
4. test_run_evaluation_tolerance_chars_zero：public per_doc 没有
   _tolerance_chars（被剥离）。修复：改为检查 metrics 中
   chunk_boundary_precision 存在。
5. summary.success_rates.pipeline_success.value 不存在：
   实际结构是 {success_count, total, rate}。修复：改为 rate 字段。

### 下一步建议
- 候选 FW：evaluation/annotation_metrics.py 第四轮（194 行）
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FY：app/models.py 第三轮（154 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FW（evaluation/annotation_metrics.py 第四轮）。
annotation_metrics 是 PRF 计算核心，194 行，涉及 chunk_boundary_prf、
figure_caption_prf 等独立函数。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 119 后）：8795 pass / 0 fail / 13 skip（HEAD `787fce5`）

---

## Round 120（2026-08-05）：evaluation/annotation_metrics.py 第四轮（edges4）

### 范围
- 文件：`tests/test_annotation_metrics_edges4.py`（新增，732 行）
- 目标：`evaluation/annotation_metrics.py`（194 行，已有 310 测试）
- 新增测试：67 个
- 提交：`4ef964e`

### 覆盖深度
- **figure_caption_prf 第四轮**：
  - 各种 input（None/空 dict/正常 dict）keys 集合精确 3 项
  - precision/recall/f1 value 全为 None（不允许 falsy）
  - precision/recall/f1 reason 全为 PARSER_DOES_NOT_EMIT_RELATIONS
  - idempotent 多次调用
  - 即使 annotation 含 figure_caption_anchors 仍 null
  - value 字段 None 类型，reason 字段 str 类型
- **chunk_boundary_prf tolerance 边界**：
  - 距离 = tolerance → 匹配
  - 距离 = tolerance + 1 → 不匹配
  - tolerance=0：仅精确匹配
  - tolerance=0：距离 1 不匹配
- **predicted 数量**：
  - 2 chunks → 1 predicted
  - 3 chunks → 2 predicted
  - 5 chunks → 4 predicted
- **position 大小写**：
  - "before" 小写有效
  - "AFTER" 大写视为 after（else 分支）
  - "middle" 视为 after
  - "" 视为 after
- **chunk text 特殊字符**：
  - 标点、数字、unicode 中文
- **算法细节**：
  - marker 在 stream 中两次出现 → search_from 推进
  - marker 与 chunk text 部分重叠
  - chunk.text=None 触发 fallback
  - marker at stream start/end
- **多 predicted 多 anchor**：
  - predicted 多于 anchors → precision < 1.0
  - anchors 多于 predicted（含 missing）→ recall 1.0
  - greedy 选最小距离
  - 一对一匹配：两 anchor 同 predicted → 一个成功
- **F1 计算**：
  - 完美匹配 → 1.0
  - 全无匹配 → null（recall null 时）
  - p=0.5/r=1.0 → 计算 2pr/(p+r)
- **不变性**：
  - 不修改 document/annotation
  - 多次调用结果一致
- **模块结构深度**：
  - PARSER_DOES_NOT_EMIT_RELATIONS 值精确
  - __all__ 为 list、长度 3、精确 set
  - imports：Counter/Any/normalize_text/_null/_ratio
  - figure_caption_prf/chunk_boundary_prf callable
  - docstring 提及 caption/chunk_boundary/tolerance
  - from __future__ import annotations
- **签名深度**：
  - figure_caption_prf 2 参数（document/annotation，无默认）
  - chunk_boundary_prf 3 参数（含 tolerance_chars，默认 30）
- 无源码改动。

### 撞墙记录
1. test_chunk_boundary_one_to_one_matching_no_double_count：
   原用 "ab"+"a" 两 marker，但 search_from 推进后第二个 anchor 找不到。
   修复：改用 "a" before + "l" before 两个不同 marker，gt_positions=[0,2]。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FY：app/models.py 第三轮（154 行）
- 候选 FZ：evaluation/schema.py 第三轮（86 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：所有 evaluation/* 模块已完成 edges4。下一轮转 app/* 模块。
选 FX（app/parsers/fallback_parser.py 第五轮）。fallback_parser 是核心
解析器，630 行最大，深度空间最大。但 5 轮已多，可考虑 FY（app/models.py
第三轮）作为短轮过渡。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 120 后）：8862 pass / 0 fail / 13 skip（HEAD `4ef964e`）

---

## Round 121（2026-08-05）：app/models.py 第三轮（edges3）

### 范围
- 文件：`tests/test_models_edges3.py`（新增，817 行）
- 目标：`app/models.py`（154 行，已有 203 测试）
- 新增测试：104 个
- 提交：`4837abf`

### 覆盖深度
- **SCHEMA_VERSION 精确值**：
  - = "0.1.0"、is str、3 段
  - major=0, minor=1, patch=0
- **ElementType / SourceType Literal**：
  - typing.get_args 解析
  - ElementType 8 成员精确集合
  - SourceType 6 成员精确集合
- **Element __post_init__**：
  - content=" "/"\t"/"\n" → truthy → 通过
  - resource_path=" " → truthy → 通过
  - content+resource_path 都 None/"" → 抛 ValueError
  - element_id="\t"/"   " → truthy → 通过
  - confidence 0.0/1.0 显式
  - metadata/parent_id 默认与传值
  - to_dict 8 keys 精确集合
- **Chunk __post_init__**：
  - text 单字符 / chunk_id 单字符 / 单 source_element_id
  - text="\n" 单字符 → 通过
  - 特殊字符 / unicode 文本
  - metadata/source_spans 默认值
  - metadata/source_spans 实例隔离
  - to_dict 5 keys 精确集合
- **Relation 深度**：
  - to_dict 4 keys、默认 metadata={}
  - from_id/to_id/type 空串接受
  - unicode ids、metadata 传值
- **WarningRecord 深度**：
  - 必填 code/reason、details 默认 None
  - to_dict 2/3 keys（依 details）
  - details={} falsy 但 not None → 包含
- **ErrorRecord 深度**：
  - 必填 code/message、details 默认 None
  - to_dict 2/3 keys
  - details={} → 包含
- **Document 深度**：
  - 12 字段（6 必填 + 6 默认）
  - to_dict 13 keys（含 schema_version）
  - keys 精确集合
  - metadata/elements 实例隔离
- **模块结构**：
  - imports dataclass/field/asdict/Any/Literal/Optional
  - SCHEMA_VERSION/ElementType/SourceType 顶层
  - 6 个 dataclass 类全存在
  - docstring 提及 dataclass
  - from __future__ import annotations
- **dataclass 类属性**：
  - 所有 6 个类 is_dataclass
  - 字段数：Element=8, Chunk=5, Relation=4,
    WarningRecord=3, ErrorRecord=3, Document=12
- 无源码改动。

### 撞墙记录
1. test_document_required_fields_count / to_dict_keys_count /
   field_count：原以为 13 字段（含 schema_version），实际 schema_version
   是模块常量，Document 类只有 12 字段，to_dict 输出 13 keys（添加
   schema_version）。修复：13→12（fields），14→13（to_dict keys）。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 FZ：evaluation/schema.py 第三轮（86 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮（已有 3 轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FZ（evaluation/schema.py 第三轮）。schema.py 较小（86 行），
但作为 Schema 校验核心，深度路径仍有空间。短轮过渡后再做 FX。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 121 后）：8966 pass / 0 fail / 13 skip（HEAD `4837abf`）

---

## Round 122（2026-08-05）：evaluation/schema.py 第三轮（edges3）

### 范围
- 文件：`tests/test_evaluation_schema_edges3.py`（新增，679 行）
- 目标：`evaluation/schema.py`（80 行，已有 358 测试）
- 新增测试：87 个
- 提交：`703f713`

### 覆盖深度
- **SCHEMAS_DIR 常量深度**：
  - 是 Path 对象、绝对路径、是目录
  - 名字精确 "schemas"
  - 包含三个 schema 文件
  - 父目录含 pyproject.toml
- **EvalSchemaError 深度**：
  - args 长度 1、值精确
  - str(e) 含 message
  - errors 默认 []、None→[]、[]保持、非空保持
  - errors 是 list 类型
  - 不继承 ValueError
  - 两实例 errors 独立
  - repr 含类名
- **_schema_path 深度**：
  - 返回 Path 对象、绝对路径
  - 不存在 name → FileNotFoundError
  - 空 name、subdir、.. 全部拒
  - 错误消息含路径
  - 三 schema 文件均可访问
- **load_schema 深度**：
  - 返回 dict
  - 多次调用返回独立 dict 对象
  - 不存在 schema → FileNotFoundError
  - schema 含 $schema/$id/type/properties
- **validate 深度**：
  - 合法实例返回 None
  - 错误消息含 schema 名字、错误计数
  - errors attribute 是 list、每项有 path/message/schema_path 三 key
  - 各字段类型正确（list/str）
- **validate_file 深度**：
  - Path/str 输入都接受
  - 不存在/目录 → FileNotFoundError
  - 空文件/坏 JSON → JSONDecodeError
  - 内容不符合 → EvalSchemaError
  - unicode 文件名/内容
  - 错误消息含路径
- **模块结构**：
  - imports：json/Path/Any/Draft202012Validator/JSValidationError
  - 5 个 public 属性 + _schema_path 私有
  - __all__ 5 项精确，不含内部
  - 所有 callable
  - docstring 提及 Schema/manifest/annotation
  - from __future__ import annotations
- **签名深度**：
  - EvalSchemaError.__init__: (self, message, errors=None)
  - _schema_path/load_schema: 1 参数
  - validate/validate_file: 2 参数
  - load_schema 返回注解 dict、validate 返回 None
- 无源码改动。

### 撞墙记录
无。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GC：app/schema.py 第三轮（独立于 evaluation/schema）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GC（app/schema.py 第三轮）。app/schema.py 是文档 JSON
Schema 校验核心，独立于 evaluation/schema，第三轮深度空间仍在。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 122 后）：9053 pass / 0 fail / 13 skip（HEAD `703f713`）

---

## Round 123（2026-08-05）：app/schema.py 第三轮（edges3）

### 范围
- 文件：`tests/test_schema_edges3.py`（新增，720 行）
- 目标：`app/schema.py`（93 行，已有 371 测试）
- 新增测试：93 个
- 提交：`875f3db`

### 覆盖深度
- **SCHEMA_PATH 常量**：
  - 是 Path/绝对路径/是文件
  - 名字 "document.schema.json"
  - 父目录 "schemas"、祖父目录含 pyproject.toml
- **SchemaValidationError 深度**：
  - args 长度 1、值精确
  - errors 默认 []、None→[]、[]保持、非空保留
  - errors 是 list 类型
  - 不继承 ValueError
  - 两实例 errors 独立
  - repr/message attribute
- **load_schema 深度**：
  - 返回 dict、独立 dict 每次调用
  - str/Path 输入都接受
  - 不存在 → FileNotFoundError（消息含路径）
  - 无参数用默认 SCHEMA_PATH
- **validate 深度**：
  - 成功返回 None
  - schema=None 用默认
  - 错误消息含计数
  - errors list 各项 3 keys（path/message/schema_path）
  - 类型断言 list/str
  - 自定义 schema dict 接受
  - 空 schema 接受任何
  - sorted by path
- **is_valid 深度**：
  - True/False 返回、bool 类型
  - 不抛 SchemaValidationError
  - 自定义 schema
  - schema=None 用默认
- **validate_file 深度**：
  - Path/str 输入
  - 不存在/目录 → FileNotFoundError
  - 空文件/坏 JSON → JSONDecodeError
  - 不符合 schema → SchemaValidationError
  - 自定义 schema
  - unicode 文件名/内容
  - 错误消息含路径
- **_silence_unused_import**：
  - 无参、返回 None、callable
  - 在模块但不在 __all__
  - 名字以 _ 开头
- **模块结构**：
  - imports json/Path/Any/Draft202012Validator/JSValidationError
  - 6 public 属性精确
  - __all__ 6 项精确
  - docstring 提及 Schema
  - from __future__ import annotations
- **签名深度**：
  - SchemaValidationError.__init__: (self, message, errors=None)
  - load_schema/path 默认 SCHEMA_PATH
  - validate/is_valid/validate_file: 2 参数，schema 默认 None
  - 返回注解 dict/bool/None
- 无源码改动。

### 撞墙记录
无。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GD：app/hash.py 第三轮（46 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GD（app/hash.py 第三轮）。hash.py 是文件/文本哈希核心，
46 行短小，第三轮仍有深度空间（如各种 hash 输入、SHA256 输出格式）。
作为短轮过渡。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 123 后）：9146 pass / 0 fail / 13 skip（HEAD `875f3db`）

---

## Round 124（2026-08-05）：app/hash.py 第三轮（edges2）

### 范围
- 文件：`tests/test_hash_edges2.py`（新增，450 行）
- 目标：`app/hash.py`（24 行，已有 104 测试）
- 新增测试：53 个
- 提交：`c00b412`

### 覆盖深度
- **compute_text_hash 输入边界**：
  - bool True/False（int 子类，无 encode → AttributeError）
  - int/float/bytearray/memoryview/bytes/list/dict/None 全部拒
- **极端文本**：
  - 1MB 长文本（流式不适用但函数应能处理）
  - null byte / 仅 null byte
  - 控制字符（0x01-0x1F）
  - Latin-1 范围（0x80-0xFF）
  - 全 ASCII（0x00-0x7F）
  - 4 字节 UTF-8（emoji）
  - surrogate pair emoji（ZWJ 序列）
  - 混合 CJK + ASCII
  - 仅空白、仅标点
- **compute_file_hash 文件内容边界**：
  - 全 256 字节值
  - 全 null 字节
  - 隐藏文件（. 前缀）
  - 文件名仅数字
  - 含扩展名
  - 每个 byte 值单独文件
- **跨函数等价性**：
  - file_hash(file with X) == text_hash(X)
  - 各种 unicode/CJK/控制字符
- **稳定性**：
  - 100 次调用同结果
- **模块结构**：
  - hashlib/Path 已 import
  - 无 __all__ 定义
  - docstring 提及 SHA / source_hash
  - from __future__ import annotations
- **签名深度**：
  - file_hash: 1 参数 (path: str | Path) → str
  - text_hash: 1 参数 (text: str) → str
- **错误消息**：
  - "hash" 关键字、含路径
- 无源码改动。

### 撞墙记录
1. test_file_text_hash_equivalence_control_chars：write_text 在 Windows
   会翻译换行符（\n → \r\n）。修复：用 write_bytes(content.encode)
   避免 newline translation。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GE：app/pipeline.py 第五轮（216 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GE（app/pipeline.py 第五轮）。pipeline 是核心入口，
216 行，是各个测试调用的核心函数。第五轮深度空间仍在。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 124 后）：9199 pass / 0 fail / 13 skip（HEAD `c00b412`）

---

## Round 125（2026-08-05）：app/pipeline.py 第五轮（补 edges3）

### 范围
- 文件：`tests/test_pipeline_edges3.py`（新增，699 行）
- 目标：`app/pipeline.py`（216 行，已有 400 测试）
- 新增测试：83 个
- 提交：`991ab3e`

### 覆盖深度
- **get_parser 深度（类型断言）**：
  - 6 个 parser 名返回对应类型实例
  - 全部是 Parser 子类
  - 未知 name → ValueError，消息含完整支持列表
  - 大小写敏感、空串、含空白均拒
  - 两次调用返回独立实例
  - fallback/kreuzberg 接受 image_output_dir 参数
- **image_output_dir_for 深度**：
  - None → None；str/Path → Path
  - 短 hash 截断安全；空 hash name="images-"
  - name 格式 "images-<16 hex>"
  - parent 与 output_path.parent 一致
  - 绝对/相对路径保留输入特性
  - 一致性：同输入同输出
- **process_single 签名深度**：
  - 5 参数（input_path/output_path/parser_name/max_chars/write_json）
  - parser_name/max_chars/write_json 是 KEYWORD_ONLY
  - 默认值：output_path=None, parser_name="fallback", max_chars=800, write_json=True
  - 返回 tuple 注解
- **validate_only 深度**：
  - 返回 (bool, str) 元组
  - 缺文件 → False + 消息含"missing"
  - 坏 JSON → False + "JSON" 关键字
  - 不符合 schema → False
  - 合法 → True + "OK"
  - str/Path 输入都接受
- **模块结构**：
  - imports 完整（json/Path/Any/StructuralChunker/compute_file_hash/
    Document/ErrorRecord/Parser/ParserError/6 parser 类/
    SchemaValidationError/validate）
  - __all__ 4 项精确（get_parser/image_output_dir_for/process_single/validate_only）
  - 全 public（无 _ 前缀）
  - docstring 提及 Pipeline/校验
  - from __future__ import annotations
- **签名深度**：
  - get_parser: (name, image_output_dir=None)
  - image_output_dir_for: (output_path, source_hash) 均必需
  - process_single: 见上
  - validate_only: (json_path) → tuple[bool, str]
- 无源码改动。

### 撞墙记录
1. test_validate_only_returns_ok_for_valid：构造的 element 缺 parent_id/
   confidence/metadata 等必需字段。修复：补全 schema 必需字段。
2. test_image_output_dir_for_output_path_default_none：output_path 是
   必需参数（无默认）。修复：改为 assert default is empty。

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GF：app/cli.py 第三轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GF（app/cli.py 第三轮）。cli.py 是用户接口入口，
第三轮深度空间仍在（subcommand、参数解析、退出码等）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 125 后）：9282 pass / 0 fail / 13 skip（HEAD `991ab3e`）

---

## Round 126（2026-08-05）：app/cli.py 第五轮（edges5）

### 范围
- 文件：`tests/test_cli_edges5.py`（新增，1115 行）
- 目标：`app/cli.py`（535 行，已有 494 测试）
- 新增测试：130 个
- 提交：`aa939c0`

### 覆盖深度
- **_EXTENSION_TO_PARSER 内容精确**：
  - 9 个扩展名全覆盖（.pdf/.docx/.md/.markdown/.html/.htm/.txt/.text/.ipynb）
  - pdf→fallback, docx→fallback, md/markdown→markdown,
    html/htm→html, txt/text→text, ipynb→ipynb
- **_infer_parser_name 深度**：
  - 大小写不敏感（.PDF/.MD/.TXT/.IPYNB 等大写）
  - 无扩展名 → fallback
  - 未知扩展名（.json/.csv/.xml/.yaml）→ fallback
- **_iter_supported_files 深度**：
  - 空目录、仅不支持文件、排序输出
  - 递归 vs 非递归
  - 9 个扩展名全覆盖、大小写不敏感
- **_relative_output_path**：
  - 顶层、子目录、完整文件名保留
- **_preview 深度**：
  - None/空/短文本不截断
  - 长文本截断带省略号
  - 宽度边界（exact 宽度不截断、+1 触发截断）
  - 自定义宽度、空白折叠、unicode
- **_load_document_json 深度**：
  - 缺文件/坏 JSON/合法/数组 root/unicode 文件名
- **_format_summary 深度**：
  - minimal/缺字段、hash 截断 16 字符
  - counts/warnings 截断 5 个、errors、avg chars
- **_format_elements_list 深度**：
  - 空、limit 截断、limit=0、parent_id 显示
- **_format_chunks_list 深度**：
  - 空、基础、spans 显示/不显示、limit 截断
- **_emit_structured_error 深度**：
  - stderr 输出、合法 JSON、required keys、extra kwargs
- **main 退出码**：
  - validate 成功=0、validate 失败=1、inspect 缺文件=1、参数错误=2
- **模块结构**：
  - imports 完整（argparse/json/Path/sys/dataclasses）
  - helpers 全 callable
  - docstring 提及 PDF/DOCX/validate/inspect
- **签名深度**：
  - main argv 默认 None
  - 各 helper 参数精确

### 撞墙记录
（无 — Round 126 一次通过，130 测试全 pass）

### 下一步建议
- 候选 FX：app/parsers/fallback_parser.py 第五轮（630 行）
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GH：evaluation/manifest.py 第五轮
- 候选 GI：evaluation/runner.py 第五轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 FX（app/parsers/fallback_parser.py 第五轮）。
fallback_parser 是默认 parser 路径，630 行体量最大，
第五轮深度空间仍在（PDF/DOCX 分支、element 字段填充、warning/error 路径）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 126 后）：9412 pass / 0 fail / 13 skip（HEAD `aa939c0`）

---

## Round 127（2026-08-05）：app/parsers/fallback_parser.py 第五轮（edges5）

### 范围
- 文件：`tests/test_parsers_fallback_edges5.py`（新增，1291 行）
- 目标：`app/parsers/fallback_parser.py`（630 行，已有 536 测试）
- 新增测试：194 个
- 提交：`a4ab7e2`

### 覆盖深度
- **_CAPTION_RE 模式内容**：
  - 含 Table/Figure/Fig/表/图 关键字
  - 含 0-9 与 ０-９（全角）数字范围
  - 含 ./:/、 分隔符
  - flags 含 IGNORECASE
- **_is_caption 多形式覆盖**：
  - 9 种 caption 形式全 pass（Figure 1./Fig.1/Fig 1/Table 1./表 1./图 1 等）
  - 数字 0 开头、多位数字、0 数字
  - 大小写不敏感（FIGURE）
  - 反例：Table of contents（词后无数字）、中间出现（必须开头）
- **_classify_pdf_paragraph 深度**：
  - 空串/纯空白 → paragraph
  - 81 字符 → paragraph
  - 80 字符无标点 → heading（level=0）
  - 80 字符含 . → paragraph
  - heading meta 含 level + heuristic 两 key
  - caption 优先级 > heading
  - 返回 tuple[str, dict]
- **_image_filename 深度**：
  - doc-1 → 1, doc-123 → 123, doc-doc-1 → 1（全替换）
  - 无 doc- 前缀原样保留
  - index 0/99/100 格式
  - 自定义 ext
- **_rows_to_markdown 深度**：
  - 单元格含 | 与换行符保留
  - 单行表格（仅 header）= 2 行输出
  - 1 header + 2 body = 4 行
  - 分隔行每列一个 ---
  - int/float/None 转换
- **_lines_to_para 深度**：
  - 多行 word 融合
  - bbox 顺序 [x0, top, x1, bottom]
  - word 缺 top/bottom 默认 0
  - 同行 word 按 x0 排序
- **_group_words_to_paragraphs 深度**：
  - 空/单 word/同 y 双 word 一段
  - 返回 list[dict]，每 dict 有 text + bbox
- **_is_heading_style 深度**：
  - Title/title/Title 带空白 → (True, 1)
  - Heading 1/2/10 → (True, 1/2/10)
  - Heading 无 level → ValueError → (True, 1)
  - Heading abc → (True, 1)
  - Heading -1 → (True, 1)（max(1, -1)）
  - 大小写不敏感
  - Normal/List Paragraph/Quote → (False, 0)
- **_extract_inline_image_rids 深度**：
  - 空 XML → []
  - 返回 list 类型
  - 每项是 str
- **_save_image 深度**：
  - 返回 Path/写 bytes/多层目录创建/自定义 ext
  - 文件名格式精确/覆盖/连续 index
- **FallbackParser class 深度**：
  - name/version（含 3 个库关键字）
  - 继承 Parser
  - __init__ 默认 None/Path/str/空串 → None/两实例独立
- **FallbackParser.parse 错误路径**：
  - 缺文件 → ParserError(file_not_found) + details
  - 目录 → ParserError(file_not_found)
- **_render_pdf_image_region 兼容包装**：
  - callable/签名 5 参数/dpi 默认 144/返回注解
- **模块结构**：
  - imports 完整（re/Path/Any/Document/Element/WarningRecord/
    Parser/ParserError/detect_source_type/make_document_id）
  - 19 个 helper 函数与常量全部存在
  - __all__ 1 项精确（仅 FallbackParser）
  - 3 个版本常量（_PDFPLUMBER_VERSION/_PDFIUM_VERSION/_DOCX_VERSION）
  - docstring 提及 pdfplumber + python-docx
  - from __future__ import annotations
- **签名深度**：
  - 各函数签名/默认值/返回注解精确

### 撞墙记录
1. test_is_caption_chinese_figure_with_colon：pattern `[\.、:\s]` 只含 ASCII
   冒号，不含全角 ：。修复：改为 ASCII 冒号。
2. test_image_filename_multiple_doc_prefix：str.replace 替换所有出现，
   "doc-doc-1" → "1"（非 "doc-1"）。修复：assert 等于 "image_1_..."。
3. test_rows_to_markdown_two_body_rows：1 header + 2 body = 4 行（含分隔行），
   不是 3 行。修复：len == 4。

### 下一步建议
- 候选 GA：evaluation/cli.py 第五轮（243 行）
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GH：evaluation/manifest.py 第五轮
- 候选 GI：evaluation/runner.py 第五轮
- 候选 GJ：evaluation/metrics.py 第五轮
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GA（evaluation/cli.py 第五轮）。cli.py 是评测入口，
243 行体量适中，第五轮深度空间仍在（subcommand、退出码、报告格式）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 127 后）：9606 pass / 0 fail / 13 skip（HEAD `a4ab7e2`）

---

## Round 128（2026-08-05）：evaluation/cli.py 第五轮（edges5）

### 范围
- 文件：`tests/test_evaluation_cli_edges5.py`（新增，820 行）
- 目标：`evaluation/cli.py`（243 行，已有 375 测试）
- 新增测试：104 个
- 提交：`8648b90`

### 覆盖深度
- **_build_parser 深度（subparser 与参数细节）**：
  - returns ArgumentParser / prog = "evaluation.cli"
  - description 含 "评测"
  - 3 个子命令存在（run/validate-report/inspect-doc）
  - run 必需 --manifest/--output
  - --parser choices 接受 fallback/kreuzberg，拒绝 unknown
  - 默认 parser=fallback, max-chars=800, tolerance-chars=30
  - 自定义 max-chars/tolerance-chars
  - validate-report 仅位置参数 input
  - inspect-doc 位置参数 input + --tolerance-chars（默认 30）
  - command 属性存在
- **_format_metric 深度（边界情况）**：
  - None value 无 reason → "null  (None)"
  - None value 有 reason → "(reason)"
  - int/float/bool/dict/string 各类型
  - dict value 排序 by key
  - float 4 位小数四舍五入
  - 空 dict metric → null 路径
  - 多余 key 被忽略
  - name 不足 36 补足，超 36 不截断
  - list value 走 default str() 分支
- **_run_inspect_doc 深度**：
  - 缺文件 → 2 + stderr ERROR
  - 坏 JSON → 1
  - array/string/null/int/bool root → 1
  - minimal doc → 0
  - 输出含 file path/counts/metrics header
  - 缺 source_type → "unknown"
- **main 退出码矩阵**：
  - 无命令 → SystemExit 2
  - 未知命令 → SystemExit 2
  - inspect-doc 缺文件 → 2
  - inspect-doc 坏 JSON → 1
  - inspect-doc 合法 → 0
  - validate-report 缺文件 → 2
- **模块结构深度**：
  - imports 完整（argparse/json/sys/Path/ManifestError/
    load_manifest/run_evaluation/get_git_provenance/
    EvalSchemaError/validate_file）
  - 4 个函数（_build_parser/main/_format_metric/_run_inspect_doc）
  - helpers 带 _ 前缀，main 是 public
  - 不定义 __all__
  - docstring 提及 run/validate-report/inspect-doc/manifest/parser
  - from __future__ import annotations
  - __main__ guard 存在
  - utf-8 reconfigure block 存在
- **签名深度**：
  - _build_parser: () → ArgumentParser
  - _format_metric: (name, metric) → str
  - _run_inspect_doc: (args) → int
  - main: (argv=None) → int

### 撞墙记录
（无 — Round 128 一次通过，104 测试全 pass）

### 下一步建议
- 候选 GB：app/chunkers/structural.py 第四轮
- 候选 GH：evaluation/manifest.py 第五轮
- 候选 GI：evaluation/runner.py 第五轮
- 候选 GJ：evaluation/metrics.py 第五轮
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 候选 GL：evaluation/report.py 第五轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GB（app/chunkers/structural.py 第四轮）。
structural.py 是结构分块核心算法，第三轮已建立基础，
第四轮可深入 chunk_id/source_element_ids/heading 边界等深度路径。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 128 后）：9710 pass / 0 fail / 13 skip（HEAD `8648b90`）

---

## Round 129（2026-08-05）：app/chunkers/structural.py 第五轮（edges5）

### 范围
- 文件：`tests/test_chunker_edges5.py`（新增，1255 行）
- 目标：`app/chunkers/structural.py`（388 行，已有 506 测试）
- 新增测试：175 个
- 提交：`b276136`

### 覆盖深度
- **_PART_* 常量值精确**：
  - _PART_TEXT=0, _PART_ELEMENT_ID=1, _PART_START=2, _PART_END=3
  - 4 个 distinct，按顺序递增
- **_SplitPiece 深度**：
  - is_dataclass / frozen / hashable
  - boundary_after 三个值（whitespace/forced_char/None）
  - 默认 start=0/end=0
  - 字段数 4 + 字段名精确
- **_SENTENCE_SPLIT_RE pattern 内容**：
  - compiled pattern / 含中英文标点
  - 用 lookbehind (?<=)
  - 中文/英文/混用句子切分
  - 标点后无空白不切
- **_HARD_BREAK_LANGS 内容**：
  - is_tuple / length 6 / exact set
- **_WHITESPACE_RE 行为**：
  - pattern `\s+` / sub 各种空白折叠
- **normalize_text 深度**：
  - 空串/None/单空白/全空白 → ""
  - 中英文混合/emoji 保留
  - idempotent / returns str
- **_hard_split_with_whitespace_fallback 深度**：
  - 空/全空白 → []
  - text < max → 单 piece
  - text = max → 单 piece
  - text > max with whitespace → 多 piece，whitespace 边界
  - text > max no whitespace → forced_char
  - leading whitespace 跳过
  - each piece ≤ max_chars
- **_split_long_text 深度**：
  - 空/纯空白 → []
  - 短文本 → 单 piece
  - exact max_chars → 单 piece
  - 长 paragraph → 多 piece
  - 入口 strip
- **_ChunkBuffer 深度**：
  - is_dataclass / 默认工厂独立
  - 字段数 3 + 字段名精确
  - push_text/length/is_empty/flush 各种场景
  - flush metadata 含 strategy/max_chars/char_count
  - source_spans 每项含 element_id/start/end
  - chunk_id 格式与 counter
  - dedup source_element_ids 保留首次出现顺序
- **StructuralChunker.__init__ 深度**：
  - 默认 800 / 显式 / 32 minimum / 31 拒绝 / 0 拒绝 / 负数拒绝
  - ValueError message 含 max_chars 值 + "过小"
- **StructuralChunker.chunk 深度**：
  - 不同 type 的 strategy 值（sequential/isolated_table/isolated_caption/
    long_paragraph_sentence_split）
  - heading 硬边界封口
  - image element 跳过
  - 空/纯空白 paragraph 不参与分块
  - chunk_id 格式与递增
  - source_spans 含 element_id
- **_element_text_with_span 深度**：
  - image / 空 content / None content / 纯空白 → ("",0,0)
  - lstrip 长度推算 start
  - 内部空白保留
- **模块结构深度**：
  - imports 完整（re/dataclass/field/Any/Chunk/Document/Element）
  - 4 个常量 + 3 个 dataclass/class + 4 个 helper 全部存在
  - __all__ 2 项（StructuralChunker + normalize_text）
  - 全 public（无 _ 前缀）
  - docstring 提及分块/heading/source_spans
  - from __future__ import annotations
- **签名深度**：
  - normalize_text: (s) → str
  - StructuralChunker.__init__: (self, max_chars=800)
  - StructuralChunker.chunk: (self, document) → list[Chunk]
  - _ChunkBuffer.flush: strategy/max_chars 是 KEYWORD_ONLY
  - _ChunkBuffer.push_text: (self, text, element_id, start, end)

### 撞墙记录
1. test_sentence_split_re_split_chinese_sentences：pattern `(?<=[...])\s+`
   需要空白才切，中文标点直接相邻不切。修复：assert 整段不切。
2. _make_element helper：Element 的 __post_init__ 要求 content 或
   resource_path 至少一个非空。修复：空 content 时提供 resource_path="(placeholder)"。
3. docstring 中含 `\s+` 触发 SyntaxWarning。修复：用 r"""raw string"""。

### 下一步建议
- 候选 GH：evaluation/manifest.py 第五轮
- 候选 GI：evaluation/runner.py 第五轮
- 候选 GJ：evaluation/metrics.py 第五轮
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 候选 GL：evaluation/report.py 第五轮
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GH（evaluation/manifest.py 第五轮）。manifest 已有 4 轮，
第五轮可深入 _is_absolute_like/_has_backslash/ManifestError 边角。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 129 后）：9885 pass / 0 fail / 13 skip（HEAD `b276136`）

---

## Round 130（2026-08-05）：evaluation/manifest.py 第五轮（edges5）

### 范围
- 文件：`tests/test_evaluation_manifest_edges5.py`（新增，1228 行）
- 目标：`evaluation/manifest.py`（239 行，已有 425 测试）
- 新增测试：176 个
- 提交：`9127e38`
- **里程碑：测试总数突破 10000（10061 pass）**

### 覆盖深度
- **_is_absolute_like 微边界**：
  - 空串/单字符/双字符/三字符相对路径
  - POSIX 绝对 /foo / Windows C:\foo / C:/foo
  - 大小写盘符
  - 盘符无分隔符 C:foo
  - ./foo / ../foo
  - 数字/下划线/emoji 首字符（非 alpha）
  - 中文 unicode 首字符（isalpha True → 视为盘符）
- **_has_backslash 边界**：
  - 单/多/前/后/仅 backslash
  - 空串/unicode 无 backslash
- **ManifestError 深度**：
  - 继承 Exception，不继承 ValueError/KeyError
  - args 行为（0/1/多）
  - raise/except 语义
  - 不被 ValueError 捕获
- **DocumentEntry 字段类型精确**：
  - 10 字段，类型验证（str/Path/tuple/dict/None）
  - frozen=True，hashable，in set
  - equality/inequality
- **ExpectedFailure 字段类型精确**：
  - 5 字段，类型验证
  - frozen=True，hashable
- **Manifest 字段类型精确**：
  - 5 字段，类型验证
  - frozen=True，hashable
  - properties 行为：file_count/pdf_count/docx_count/content_group_count/categories_covered
- **_resolve_relative_path 深度**：
  - 正常/子目录/含 ./ 与 ../
  - field_name 在各种错误消息中
  - 解析后位于 root 外 → ManifestError
- **_detect_project_root 深度**：
  - file/dir 输入
  - 多 pyproject.toml → 最近优先
  - 无 pyproject.toml
- **load_manifest 深度**：
  - signature/默认值
  - 缺文件/坏 JSON/version 不匹配
  - str/Path 输入
  - 返回 Manifest 实例
  - 路径解析/categories 转 tuple
- **模块结构深度**：
  - imports 完整（json/dataclass/Path/Any/MANIFEST_VERSION/validate）
  - __all__ 5 项精确（ManifestError/Manifest/DocumentEntry/ExpectedFailure/load_manifest）
  - 全 public（无 _ 前缀）
  - 9 个内部 helper 全部 callable
  - docstring 提及 path/relative/project root
  - from __future__ import annotations
- **签名深度**：
  - 各函数返回注解（bool/Path/Manifest）
  - load_manifest 双参数与默认值
  - 5 个 property 的签名

### 撞墙记录
1. test_is_absolute_like_unicode_first_char：中文字符 .isalpha() 也返回 True，
   所以 "中:/foo" 会被识别为 Windows 盘符形式（True）。修复：assert True。
2. test_load_manifest_manifest_version_mismatch_raises：schema enum 校验
   先于我们代码里的 version 二次校验，所以非 enum 值会被 EvalSchemaError 拦截。
   修复：改 assert EvalSchemaError。

### 下一步建议
- 候选 GI：evaluation/runner.py 第五轮
- 候选 GJ：evaluation/metrics.py 第五轮
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 候选 GL：evaluation/report.py 第五轮
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GI（evaluation/runner.py 第五轮）。runner 已有 4 轮，
第五轮可深入 _load_annotation/_process_one/run_evaluation 边角。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 130 后）：10061 pass / 0 fail / 13 skip（HEAD `9127e38`）

---

## Round 131（2026-08-05）：evaluation/runner.py 第五轮（edges5）

### 范围
- 文件：`tests/test_evaluation_runner_edges5.py`（新增，1053 行）
- 目标：`evaluation/runner.py`（227 行，已有 404 测试）
- 新增测试：97 个
- 提交：`b2af63d`

### 覆盖深度
- **_load_annotation 边界**：
  - 签名（1 参数 + 注解）
  - None/缺文件/目录/空文件/纯空白 → None
  - object/array/int/string/null/bool 各种 JSON 类型
  - 嵌套 dict（修正 list index）
  - unicode 文件名与内容
  - 坏 JSON/truncated → None
- **_process_one 深度**：
  - 签名（4 参数）
  - 返回 tuple 5 元素
  - 失败时 document=None + error 含 code/message
  - parser_version=None（失败时）
  - image_dir=None（document None 时）
  - elapsed >= 0 + float 类型
  - 创建 _per_doc 目录
- **run_evaluation 深度**：
  - 签名（5 参数含 tolerance_chars）
  - parser_name/max_chars/tolerance_chars 是 KEYWORD_ONLY
  - 默认 fallback/800/30
  - 创建输出文件/返回 dict
  - 报告含 report_version/provenance/devset/summary/per_doc/expected_failures
  - 创建嵌套输出目录
  - idempotent
- **报告字段内容深度**：
  - provenance 含 parser_name/max_chars/evaluator_version
  - devset 含 status
  - summary 含 success_rates
  - per_doc 各项含 doc_id/source_type/metrics/wall_time_seconds
  - wall_time_seconds 含 total/parse/chunk + parse_reason/chunk_reason
  - public per_doc 不含 _ 前缀字段
  - expected_failures 各项含 4 字段
  - matches 字段 true/false 与 actual_error_code
- **时间字段行为**：
  - elapsed 是 float
  - wall_time total 是 float
  - parse/chunk 是 None
  - parse_reason/chunk_reason 是 "not_instrumented"
- **模块结构深度**：
  - imports 完整（json/time/Path/Any/process_single/image_output_dir_for/
    REPORT_VERSION/chunk_boundary_prf/figure_caption_prf/
    compute_automatic_metrics/aggregate_summary/build_provenance/
    build_devset_section）
  - __all__ 1 项（run_evaluation）
  - 3 个函数全部 callable
  - docstring 提及 total/not_instrumented/image/pipeline
  - from __future__ import annotations

### 撞墙记录
1. test_load_annotation_nested_dict：list [1,2,{"d":"e"}] 索引 2 才是 dict
   （我之前写成索引 3，超界）。修复：assert [2]。
2. test_run_evaluation_signature_four_params：实际有 5 个参数
   （含 tolerance_chars）。修复：改 5 参数。
3. test_report_provenance_has_report_version_field：provenance 实际不
   重复 report_version（在顶层），但含其他字段。修复：换成验证
   devset_status 不在 provenance 里。

### 下一步建议
- 候选 GJ：evaluation/metrics.py 第五轮
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 候选 GL：evaluation/report.py 第五轮
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GJ（evaluation/metrics.py 第五轮）。metrics 已有 4 轮，
第五轮可深入 _strip_unicode_whitespace/_is_valid_bbox/_null/_ratio
等 helper 边界与 compute_automatic_metrics 全字段验证。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 131 后）：10158 pass / 0 fail / 13 skip（HEAD `b2af63d`）

---

## Round 132（2026-08-05）：evaluation/metrics.py 第五轮（edges5）

### 目标
- 给 evaluation/metrics.py（381 行，已有 624 测试）补第五轮 edges
- 深入 helper 函数边界、Unicode whitespace、bbox 校验、compute_automatic_metrics 全字段

### 改动
- 新增 `tests/test_evaluation_metrics_edges5.py`（182 测试）
- 仅测试，不动业务代码（保持 evaluation/ → app/ 单向依赖）

### 覆盖要点
- **_null/_ratio/_bool_metric/_int_metric 深度**：
  - 返回 dict 结构（value/reason 字段）
  - _bool_metric 接受 Python truthy（不强制 bool 类型）
  - _int_metric 接受任意 int（含负数）
  - _ratio 边界（0/1/正常比例）与 NaN 处理
- **_strip_unicode_whitespace 全 Unicode 空白**：
  - ASCII whitespace（空格/\t/\n/\r/\f/\v）
  - NBSP（\xa0）、em space（ ）、en space（ ）
  - ideographic space（　）
  - line separator（ ）、paragraph separator（ ）
  - 中间空白也删除（不只是 strip 两端）
- **_is_valid_bbox 边界**：
  - 必须 4 元素
  - int/float 均可
  - bool 拒绝（Python bool 是 int 子类）
  - NaN/Inf 拒绝（math.isfinite 校验）
  - tuple 拒绝（要求 list）
- **_pdf_locator_ratio 深度**：
  - page 必须 int 且 ≥1
  - bbox 4 类元素要求 bbox（heading/paragraph/caption/list_item）
  - 非 4 类元素仅要求 page
- **_docx_locator_ratio 深度**：
  - 仅校验 structural keys（paragraph_index/element_index 等）
  - 拒绝 page/bbox（DOCX 不该有）
- **_image_resource_ratio**：
  - 用 tmp_path 真实写文件
  - resource_path 不存在 → 计入无效
- **_chunk_reference_ratio**：
  - 空 chunks → ratio=None
  - 部分匹配（部分 source_element_ids 不存在）→ 比例下降
- **_text_preservation v1.1 口径 D**：
  - 删除全部 Unicode 空白后比较
  - equal = expected_sequence == actual_sequence
  - precision/recall 用 Counter multiset
  - 非图像元素参与（image content 当作空）
- **_heading_boundary_ratio**：
  - 无 heading → None
  - 每个 heading 必须独立 chunk
- **_silent_drop_count**：
  - expectations.element_count_by_type 必须存在
  - 无 expectations → None
  - 比例按类型对比 element_count_by_type 与 expectations
- **compute_automatic_metrics 综合验证**：
  - document=None 时返回 14 keys（pipeline_success/error_code/schema_valid + 11 null）
  - 成功路径所有 14 keys 有值
  - per-key value/reason 结构正确
- **模块常量**：
  - _TEXT_TYPES = 7 项（heading/paragraph/list_item/table/caption/header/footer）
  - _PDF_BBOX_REQUIRED_TYPES = 4 项
  - _NOT_EVALUATED 为 list
- **签名验证**：所有 helper 函数 callable + 参数数

### 撞墙记录
1. test_strip_unicode_whitespace_mixed：函数实际**删除全部空白**
   （含中间），不是只 strip 两端。修复：assert "ab\xc1d"。
2. test_compute_metrics_document_none_13_keys：实际 14 keys
   （pipeline_success + error_code + schema_valid + 11 个 null 指标）。
   修复：assert 14 + set 比较。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 132 后）：10340 pass / 0 fail / 13 skip（HEAD `bbf578f`）

### 下一步建议
- 候选 GK：evaluation/annotation_metrics.py 第五轮
- 候选 GL：evaluation/report.py 第五轮
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GK（evaluation/annotation_metrics.py 第五轮）。该模块处
理 annotation 文件解析与 manifest expect_failure 比对，第五轮可深入
错误码匹配、annotation 字段缺漏、compare 逻辑等边界。

---

## Round 133（2026-08-05）：evaluation/annotation_metrics.py 第五轮（edges5）

### 目标
- 给 evaluation/annotation_metrics.py（194 行，已有 377 测试）补第五轮 edges
- 深入 chunk_boundary_prf 算法边界、figure_caption_prf 结构、空白规范化

### 改动
- 新增 `tests/test_annotation_metrics_edges5.py`（80 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **figure_caption_prf 深度**：
  - 每项 value/reason 字段
  - 不含 _tolerance_chars / _missing_markers
  - 三个 dict 对象互不相同
  - 任意额外 dict 键不影响输出
  - annotation 含 figures/captions 字段仍 null
  - 大量 chunks 不影响输出（始终 null）
- **chunk_boundary_prf 空白规范化**：
  - chunk text 内双空格 → normalize 后单空格
  - chunk text 前后空格 → strip
  - marker 中间空格仍能找到
  - marker = chunk text 末尾 → 精确匹配
  - marker = 下个 chunk 开头 + position="before" → 偏移 1
  - position="before" + tolerance=1 → 匹配
- **chunk_boundary_prf 单 chunk 边界**：
  - len(chunks)==1 + anchors 非空 → recall=0.0
  - len(chunks)==1 + anchors 空 → recall null
  - chunks=[] + anchors 空 → 全 null
  - chunks=[] + anchors 非空 → recall=0.0
- **chunk_boundary_prf missing_markers**：
  - 部分缺失 → _missing_markers 含缺失项
  - 全缺失 → 含全部，gt_positions 为空
  - 全找到 → 无 _missing_markers 字段
  - 空 marker → 视为缺失
- **chunk_boundary_prf 一对一贪心匹配**：
  - 2 predictions + 2 GTs + tolerance=0 → 全匹配
  - 1 prediction + 2 anchors → 只能匹配 1，recall=0.5
  - 距离超过 tolerance → 不匹配
- **_tolerance_chars 字段**：
  - 始终在 chunk_boundary_prf 输出（document=None/无 annotation/单 chunk/无 anchors/全匹配 五个分支）
  - value = 传入参数（含负数）
  - reason = None
- **document/annotation None 与空 dict 分支**：
  - document=None → "pipeline_failed"
  - annotation=None / {} / 0 → "no_annotation"
  - document 无 chunks 键 → 视为 []
  - annotation 无 chunk_boundary_anchors 键 → 视为 []
- **chunk text 在 stream 中找不到**：
  - 空 chunk text → find 返回 pos，predicted 加 0
- **f1 计算**：
  - p/r 都 null → f1 null
  - p=0/r=0 → denom=0 → f1=0.0（不是 null）
  - p=0.5/r=1.0 → f1 ≈ 0.667
  - p=1/3/r=1.0 → f1 ≈ 0.5
- **不修改输入**：doc/ann 在调用前后相等
- **模块结构**：
  - __all__ 是 list，3 项，顺序固定
  - PARSER_DOES_NOT_EMIT_RELATIONS 是 str
  - imports 完整（Counter/Any/normalize_text/_null/_ratio）
  - docstring 提及 figure_caption/chunk_boundary/tolerance/null
- **签名**：
  - figure_caption_prf 2 参数（document, annotation），无默认
  - chunk_boundary_prf 3 参数，tolerance_chars 默认 30
  - 所有参数 POSITIONAL_OR_KEYWORD
  - 返回类型注解存在
- **JSON 可序列化**：figure_caption_prf / chunk_boundary_prf 输出可 json.dumps

### 撞墙记录
1. test_chunk_boundary_chunk_text_with_double_spaces_normalized：原来
   marker="beta gamma" position=after → 位置 16，与 predicted=10 偏 6，
   tolerance=0 不匹配。修复：marker 改为 "alpha beta"，position=after
   → 位置 10，与 predicted=10 完美匹配。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 133 后）：10420 pass / 0 fail / 13 skip（HEAD `ed5d750`）

### 下一步建议
- 候选 GL：evaluation/report.py 第五轮
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GL（evaluation/report.py 第五轮）。report 已有 4 轮，第五轮
可深入 provenance 字段、summary 聚合、report_version 检查、JSON 序列化。

---

## Round 134（2026-08-05）：evaluation/report.py 第五轮（edges4）

### 目标
- 给 evaluation/report.py（200 行，已有 371 测试）补第五轮 edges
- 深入 provenance/devset/summary 装配与 git/dependency 拉取

### 改动
- 新增 `tests/test_evaluation_report_edges4.py`（104 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_git_provenance 深度**：
  - 返回 dict 含 git_commit/git_dirty 两个键
  - 非 git 目录 → commit=None
  - OSError / TimeoutExpired → commit=None, dirty=True
  - rev-parse returncode 非 0 → commit=None
  - rev-parse stdout 空 → commit=None
  - porcelain 输出非空 → dirty=True
  - porcelain 输出空 → dirty=False
- **get_dependency_versions 深度**：
  - 3 个固定键（pdfplumber/python-docx/pypdfium2）
  - 值是 str 或 None
  - 实际环境 pdfplumber 应有版本
  - PackageNotFoundError → None
  - 其他异常 → None
- **build_provenance 深度**：
  - 9 个键
  - evaluator_version / report_version 与常量一致
  - max_chars 转 int（含 str 输入）
  - run_timestamp_iso 是 str + 可被 datetime.fromisoformat 解析
  - parser_version None 透传
- **build_devset_section 深度**：
  - 6 个键
  - 各字段从 manifest 属性读取
  - categories_covered 支持 tuple 和 list
- **aggregate_summary 顶层结构**：
  - 4 个顶层键（counts/success_rates/ratio_macro_averages/silent_drop_total）
  - counts 含 element_count_total，结构 sum+participating_docs
  - success_rates 含 pipeline_success，结构 success_count+total+rate
  - ratio_macro_averages 含 12 项，每项 macro_average+participating_docs+not_evaluated
  - silent_drop_total 顶层
- **counts 聚合深度**：
  - participating_docs 0/1/3
  - 排除 None
- **success_rates 聚合深度**：
  - 仅 value is True 计 success（value=1 不计）
  - total 始终 = len(per_doc)
- **ratio_macro_averages 聚合深度**：
  - 1/2 个值 macro
  - 排除 None
  - 全 None → macro=None
  - value=0.0 也参与
- **silent_drop_total 聚合深度**：
  - 求和（含 0）
  - 排除 None
  - 空 → None
- **不变量**：
  - silent_drop 不混入 counts
  - pipeline_success 不混入 ratios
  - 无 overall_score
  - idempotent
  - 不修改输入
  - per_doc 无 metrics → KeyError
- **模块常量**：
  - _COUNT_METRICS = ("element_count_total",)
  - _SUCCESS_BOOL_METRICS = ("pipeline_success",)
  - _RATIO_METRICS 12 项 + 唯一 + 与 count/success 互斥 + 排除 figure_caption
- **模块结构**：
  - __all__ list, 5 项
  - imports 完整（subprocess/datetime/Path/EVALUATOR_VERSION/REPORT_VERSION）
  - from __future__ import annotations
  - docstring 提及 聚合/macro
- **签名**：
  - get_git_provenance 1 参（project_root）
  - get_dependency_versions 0 参
  - build_provenance 4 参，无默认
  - build_devset_section 1 参（manifest）
  - aggregate_summary 1 参（per_doc_results）
  - 返回类型注解存在
- **JSON 可序列化**

### 撞墙记录
1. test_aggregate_summary_handles_per_doc_without_metrics_key：实际
   aggregate_summary 用 r["metrics"] 直接索引（KeyError），不是 .get()。
   修复：用 pytest.raises(KeyError)。
2. test_build_devset_section_json_serializable：JSON 序列化时 tuple →
   list，比较不等。修复：用 list 在 FakeManifest 里。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 134 后）：10524 pass / 0 fail / 13 skip（HEAD `c39f1b0`）

### 下一步建议
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 候选 GP：evaluation/schema_validation.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GP（evaluation/schema_validation.py 第四轮）。schema 模块
负责 Document JSON 校验，第四轮可深入 if/then 分支、bbox 校验、enum
值、source_locator 结构等。

---

## Round 135（2026-08-05）：evaluation/schema_validation.py 第二轮（edges2）

### 目标
- 给 evaluation/schema_validation.py（15 行薄包装，已有 51 测试）补第二轮 edges
- 模块极小，重点覆盖异常透传、bool 转换、延迟 import、签名深度

### 改动
- 新增 `tests/test_evaluation_schema_validation_edges2.py`（30 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **异常透传**：
  - is_valid 抛 ValueError → document_passes_schema 不吞
  - is_valid 抛 TypeError → 透传
  - is_valid 不存在 → ImportError（不是 AttributeError）
- **bool() 转换语义**：
  - is_valid 返回 1 → True（Python bool 类型）
  - is_valid 返回 0 → False
  - is_valid 返回 [] → False
  - is_valid 返回 ['x'] → True
  - is_valid 返回 None → False
  - 返回值 type 是 bool（不是 int）
- **延迟 import**：
  - 函数体内 `from app.schema import is_valid`
  - 模块顶层不 import app.schema（避免循环）
  - 模块顶层有 from typing import Any
  - from __future__ import annotations
- **__all__ 深度**：
  - 是 list，1 项
  - 值 = ["document_passes_schema"]
- **签名深度**：
  - 1 参数（document），无默认，POSITIONAL_OR_KEYWORD
  - 返回注解 = bool（或 'bool'）
- **docstring**：
  - 函数 docstring 提及 is_valid
  - 模块 docstring 提及循环依赖
- **综合**：
  - 额外键不崩溃
  - idempotent
  - 不修改输入

### 撞墙记录
1. test_document_passes_schema_propagates_attribute_error：实际是
   ImportError（from import 失败），不是 AttributeError。修复：改异常类型。
2. test_document_passes_schema_return_annotation_bool：from __future__
   使注解是字符串 'bool'，不是 bool。修复：assert in (bool, "bool")。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 135 后）：10554 pass / 0 fail / 13 skip（HEAD `e9e5eff`）

### 下一步建议
- 候选 GM：app/parsers/markdown_parser.py 第四轮
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 候选 GQ：evaluation/manifest.py 第六轮（更深）
- 候选 GR：evaluation/cli.py 第六轮（更深）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GM（app/parsers/markdown_parser.py 第四轮）。markdown parser
是 fallback 之外的另一路径，第四轮可深入 ATX/SET 标题、代码块、列表
嵌套等。

---

## Round 136（2026-08-05）：app/parsers/markdown_parser.py 第五轮（edges5）

### 目标
- 给 app/parsers/markdown_parser.py（326 行，已有 587 测试）补第五轮 edges
- 深入正则模式行为、section_path 复杂场景、metadata 字段、element_id 格式

### 改动
- 新增 `tests/test_parsers_markdown_edges5.py`（115 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **正则模式深度**：
  - _ATX_HEADING_RE：1-6 #，必须空格，trailing # stripped
  - _THEMATIC_RE：3+ 字符（-* _ 混合），带空格也可
  - _FENCED_RE：3+ 反引号/波浪号，lang 含 [\w+-]
  - _UNORDERED_LIST_RE：- * + 三个 marker
  - _ORDERED_LIST_RE：N. 或 N)，多 digit 也匹配
  - _BLOCKQUOTE_RE：> 后空格可选
  - _PIPE_TABLE_SEP_RE：必须 2+ dash，支持 colon 对齐
  - _STANDALONE_IMAGE_RE：trailing 不允许文字
- **_rows_to_md 边界**：
  - 单列两行（header + body）
  - jagged rows 补空字符串
  - Unicode 单元格
- **_split_pipe_row 深度**：
  - 内部空格保留
  - 外部空格 strip
- **_is_pipe_table_start 边界**：
  - 最后一行（无下一行）→ False
  - 行匹配但分隔行不匹配 → False
  - 越界 → False
- **section_path 复杂场景**：
  - H1 → H3（跳级）
  - H1 → H2a → H3 → H2b（H2b 弹出 H3）
  - H2 → H1（H1 弹出 H2）
  - body 元素继承 section_path
  - 无 heading → locator 无 section_path 键
- **element_id 格式**：
  - e{idx:04d}（零填充 4 位）
  - 前缀 = document_id::e0000
- **confidence 默认**：0.95
- **解析全流程边界**：
  - 空文件 → md_no_content warning
  - 纯 thematic → md_no_content warning
  - 纯空白 → md_no_content warning
  - 代码块未闭合 → 收集到 EOF
  - 空代码块 → md_empty_code_block warning
- **metadata 字段**：
  - code block: kind=code_block, language=...
  - image: alt=...
  - list_item: marker=ordered/unordered, ordered=True/False
  - blockquote: kind=blockquote
  - table: row_count, col_count, source=markdown_pipe_table
  - heading: level=N
- **document 字段**：metadata={"markdown": True}，chunks/relations/errors 空
- **模块结构**：
  - _MD_EXTENSIONS = (".md", ".markdown")，tuple
  - __all__ = ["MarkdownParser"]
  - imports re/Path/Any/Document/Element/WarningRecord/Parser/ParserError/make_document_id
  - from __future__ import annotations
  - docstring 提及 ATX/setext/pipe/source_locator
- **签名**：
  - parse(self, path, source_hash) → Document
  - _parse_text(self, text, document_id) → tuple
  - MarkdownParser 是 Parser 子类
- **source_locator.line**：
  - 1-based
  - 第 3 行内容 → line=3
  - 跨元素递增

### 撞墙记录
1. test_fenced_re_lang_with_dot：正则 [\w+-]* 不含 .，整行 "ts.x" 不
   匹配。修复：改成 test_fenced_re_lang_no_dot，assert is None。
2. test_markdown_parser_parse_signature_two_params：parse 实际 3 参数
   （self, path, source_hash）。修复：改 3 参数。
3. 多处 docstring 含 \s/\w 触发 SyntaxWarning。修复：raw string。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 136 后）：10669 pass / 0 fail / 13 skip（HEAD `aee5044`）

### 下一步建议
- 候选 GN：app/parsers/html_parser.py 第四轮
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 候选 GQ：evaluation/manifest.py 第六轮
- 候选 GR：evaluation/cli.py 第六轮
- 候选 GS：app/parsers/fallback_parser.py 第六轮（已有第五轮 194 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GN（app/parsers/html_parser.py 第四轮）。html parser 与
markdown 类似规模，第四轮可深入 tag 嵌套、属性、自闭合标签等。

---

## Round 137（2026-08-05）：app/parsers/html_parser.py 第五轮（edges5）

### 目标
- 给 app/parsers/html_parser.py（446 行，已有 495 测试）补第五轮 edges
- 深入模块常量、_HTMLDocParser 状态、handle_data 边界、table 嵌套

### 改动
- 新增 `tests/test_parsers_html_edges5.py`（102 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块常量深度**：
  - _HTML_EXTENSIONS = (".html", ".htm")，tuple，2 项
  - _HEADING_LEVELS = {h1:1, ..., h6:6}，dict，6 项
  - _SKIP_TAGS = {script, style, head, title, meta, link, noscript}，set，7 项
- **_detect_html_source_type 深度**：
  - 大小写不敏感
  - 拒绝 pdf/docx/md/no_suffix
  - error details suffix 字段
- **_rows_to_md 边界**：
  - 空 / 单行 / 多行 / jagged / Unicode / 宽行
- **HtmlParser 类属性**：
  - name="html", version="stdlib/0.1.0"
  - 继承 Parser
  - _HTMLDocParser 继承 stdlib HTMLParser
- **_HTMLDocParser 初始状态**：
  - elements/warnings 空
  - _cur_kind None
  - _table_depth/_pre_depth/_blockquote_depth 0
  - _section_path/_skip_stack/_list_stack 空
- **handle_data 行为**：
  - loose text → paragraph
  - inside p/pre/blockquote 累积
  - inside script/style 忽略
- **嵌套 table warning**：
  - 内层 table 触发 html_nested_table
  - 单 table 无 warning
- **表格 cell 收尾**：
  - th/td 混合
  - 未闭合 tr 自动收尾（不崩溃）
  - row_count/col_count/source 元数据
  - confidence 0.9
- **heading 处理**：
  - h1-h6 level
  - confidence 0.95
  - 支持属性（class/id）
- **list_item**：
  - ul → unordered marker
  - ol → ordered marker
  - 多 li 累积
- **img 处理**：
  - standalone 自闭合
  - 无 src / 空 src 跳过
  - alt 默认空字符串
  - confidence 0.9
- **section_path**：
  - after h1+h2 = "A > B"
  - h2 → h1 弹出
  - 无 heading → 无 section_path 键
- **element_id 格式**：e{idx:04d}
- **综合**：复杂文档多个 block 类型
- **模块结构**：__all__/imports/docstring
- **签名**：parse 3 参，init 2 参，handle_* 各参数数

### 撞墙记录
1. test_rows_to_md_wide_row：5 列单行 header 有 6 个 |（不是 6 全文）。
   修复：用 split("\n")[0].count。
2. test_table_unclosed_tr_auto_closes：未闭合 tr 的解析行为复杂，只验
   不崩溃 + table 存在，不验具体内容。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 137 后）：10771 pass / 0 fail / 13 skip（HEAD `4c01a2d`）

### 下一步建议
- 候选 GO：app/parsers/ipynb_parser.py 第四轮
- 候选 GS：app/parsers/fallback_parser.py 第六轮
- 候选 GT：evaluation/runner.py 第六轮
- 候选 GU：evaluation/cli.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GO（app/parsers/ipynb_parser.py 第四轮）。ipynb parser 处理
Jupyter notebook JSON，第四轮可深入 cell 类型、source 拼接、metadata
解析。

---

## Round 138（2026-08-05）：app/parsers/ipynb_parser.py 第五轮（edges5）

### 目标
- 给 app/parsers/ipynb_parser.py（227 行，已有 544 测试）补第五轮 edges
- 深入 cell source 归一、kernel language 推断、nbformat 校验、locator

### 改动
- 新增 `tests/test_parsers_ipynb_edges5.py`（88 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_IPYNB_EXTENSIONS 常量**：tuple，1 项
- **_detect_ipynb_source_type 深度**：
  - 大小写不敏感
  - 拒绝 pdf/html/md/no_suffix
  - error details suffix 字段
- **_cell_source_to_text 深度**：
  - str 直传 / 空 str / list[str] / list[int] / None / int / dict
  - nbformat 标准（list 含 \n）
  - nested list str() 化
- **_extract_kernel_language 深度**：
  - 优先级：kernelspec.language > kernelspec.name > language_info.name
  - 空字符串视为 falsy 回落
  - None metadata → AttributeError（不防御）
- **IpynbParser 类属性**：name/version/继承 Parser
- **parse 全流程**：
  - markdown cell → 多 element（heading/paragraph/list）
  - code cell → paragraph（kind=code_cell, language 继承）
  - raw cell → paragraph（kind=raw_cell）
  - 空 code cell → ipynb_empty_code_cell warning
  - 空 raw cell → 静默跳过
  - 未知 cell_type → ipynb_unknown_cell_type warning
  - 非 dict cell → ipynb_bad_cell warning
  - 空 notebook → ipynb_no_content warning
- **nbformat 校验**：
  - nbformat=3 → ipynb_unsupported_version
  - nbformat=4/5 → 通过
  - nbformat 缺失 → None → 通过
  - 顶层非 dict → ipynb_bad_structure
  - cells 非 list → ipynb_bad_structure
  - 非法 JSON → ipynb_invalid_json
- **locator 深度**：
  - markdown cell 含 cell_index/cell_type/line/section_path
  - code cell 含 cell_index/cell_type（无 line）
  - section_path 仅在 cell 内累积（不跨 cell）
- **element_id 格式**：e{idx:04d}，confidence 0.95
- **Document metadata**：ipynb/nbformat/nbformat_minor/cell_count/language
- **综合**：mixed cell 类型，code/raw text stripped
- **文件 IO**：file_not_found/unsupported/OSError → read_failed
- **模块结构**：__all__/imports/docstring
- **签名**：parse 3 参，helpers 1 参

### 撞墙记录
1. test_extract_kernel_language_none_metadata：函数不防御 None，会抛
   AttributeError。修复：pytest.raises(AttributeError)。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 138 后）：10859 pass / 0 fail / 13 skip（HEAD `1afe4f1`）

### 下一步建议
- 候选 GS：app/parsers/fallback_parser.py 第六轮
- 候选 GT：evaluation/runner.py 第六轮
- 候选 GU：evaluation/cli.py 第六轮
- 候选 GV：app/chunkers/structural.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GV（app/chunkers/structural.py 第六轮）。structural chunker
已有第五轮，第六轮可深入 _split_long_text 边界、_ChunkBuffer 状态、
language-specific 分隔符。

---

## Round 139（2026-08-05）：app/chunkers/structural.py 第六轮（edges6）

### 目标
- 给 app/chunkers/structural.py（388 行，已有 681 测试）补第六轮 edges
- 深入 _SplitPiece/_ChunkBuffer/_split_long_text 算法不变量

### 改动
- 新增 `tests/test_chunker_edges6.py`（110 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_SplitPiece dataclass**：
  - 是 dataclass 且 frozen（FrozenInstanceError）
  - 默认 start=0, end=0
  - 显式 start/end 透传
  - 同值相等
  - 不同 text/boundary 不等
  - hashable
- **_hard_split_with_whitespace_fallback 深度**：
  - 空字符串 → []
  - 纯空白 → []
  - text ≤ max_chars → 单 piece，boundary=None
  - text = max_chars → 单 piece
  - 无空白 → forced_char
  - 中间空白 → whitespace
  - max_chars=1 → 每字符 piece
- **_split_long_text 深度**：
  - 空字符串 → []
  - 纯空白 → []
  - 先 strip
  - 单 piece within max
  - 无句子分隔符 → forced_char
  - 多短句子合并
  - 返回 _SplitPiece list
- **_ChunkBuffer 深度**：
  - init parts=[] counter=0
  - is_empty/length 初始
  - push 增加 length
  - push 多次累加
  - flush 空 → None
  - flush 仅空白 → None
  - flush 清空 parts
  - flush chunk_id 格式
  - flush text 用单空格 join
  - source_ids 去重（保留首次出现顺序）
  - metadata strategy/max_chars/char_count
  - source_spans 一 part 一项
- **_PART_* 常量**：int 类型，值 0/1/2/3
- **_SENTENCE_SPLIT_RE/_HARD_BREAK_LANGS/_WHITESPACE_RE**：
  - 都是 re.Pattern（前两个）/ tuple / re.Pattern
  - _HARD_BREAK_LANGS 6 项（中英各 3）
  - _WHITESPACE_RE.pattern = r"\\s+"
- **normalize_text 深度**：
  - 空/None → ""
  - 纯空白 → ""
  - 内部空白压缩为单空格
  - tab/newline 处理
  - strip 两端
  - 保留标点/Unicode
- **StructuralChunker.__init__**：
  - 默认 max_chars=800
  - max_chars < 32 raises ValueError
  - max_chars=32 OK
  - max_chars=0 / 负数 raises
- **chunk 行为**：
  - 空 elements → []
  - 单 paragraph → 单 chunk
  - heading 硬边界
  - table 隔离
  - image element 不参与分块
  - 长 paragraph 切分
  - 每 chunk 含 source_element_ids
  - chunk_id 零填充
  - metadata 字段（strategy/max_chars/char_count）
- **_element_text_with_span**：
  - paragraph → (stripped, start, end)
  - image → ("", 0, 0)
  - 前后空白 strip（start/end 反映偏移）
  - 仅空白 → 空
  - 旧接口 _element_text 也工作
- **模块结构**：__all__/imports/docstring
- **签名**：flush strategy/max_chars keyword-only，init max_chars 默认 800
- **不变量**：normalize 幂等，_split_long_text 不丢文本，chunker 不丢文本

### 撞墙记录
1. placeholder import 写法错误（`if False else None` 在 import 语句里非
   法）。修复：删除占位 import。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 139 后）：10969 pass / 0 fail / 13 skip（HEAD `2f5a925`）

### 下一步建议
- 候选 GS：app/parsers/fallback_parser.py 第六轮
- 候选 GT：evaluation/runner.py 第六轮
- 候选 GU：evaluation/cli.py 第六轮
- 候选 GW：app/pipeline.py 第五轮
- 候选 GX：app/cli.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GW（app/pipeline.py 第五轮）。pipeline 是核心入口，第五轮
可深入 process_single 流程、warning 累积、错误处理、document 装配。

---

## Round 140（2026-08-05）：app/pipeline.py 第五轮（edges5）

### 目标
- 给 app/pipeline.py（216 行，已有 483 测试）补第五轮 edges
- 深入 get_parser 工厂、image_output_dir_for、process_single 错误路径、validate_only

### 改动
- 新增 `tests/test_pipeline_edges5.py`（62 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_parser 工厂**：
  - 6 个 parser（fallback/kreuzberg/markdown/html/text/ipynb）返回对应实例
  - 全部是 Parser 子类
  - 未知 name raises ValueError，错误消息列出支持的 parser
  - image_output_dir 参数（fallback 接受，kreuzberg 忽略）
- **image_output_dir_for**：
  - output_path=None → None
  - 返回 Path 对象
  - 用 source_hash 前 16 字符
  - 短 hash 不崩溃
  - 目录在 output_path.parent 下
  - 接受 Path 输入
- **process_single 错误路径**：
  - input 不存在 → file_not_found
  - 未知 parser → unexpected_parser_error
  - text parser 不支持 .pdf → unsupported_type
  - text parser 成功路径
  - write_json=False 不写盘
  - 父目录自动创建
- **validate_only**：
  - 文件不存在 → False
  - 非法 JSON → False
  - 空文件 → False
  - 根非 dict → False
  - 返回 (bool, str) tuple
- **模块结构**：
  - __all__ 4 项（get_parser/image_output_dir_for/process_single/validate_only）
  - imports 完整（json/Path/Any/StructuralChunker/compute_file_hash/Document/ErrorRecord/Parser/ParserError/所有 parser/SchemaValidationError/validate）
  - from __future__ import annotations
  - docstring 提及 Pipeline/Schema
- **签名深度**：
  - get_parser 2 参（name 必填，image_output_dir 默认 None）
  - image_output_dir_for 2 参（都必填）
  - process_single 5 参（input_path 必填，output_path 默认 None，parser_name/max_chars/write_json 都是 keyword-only）
  - validate_only 1 参（json_path）
  - 返回类型注解存在
- **ErrorRecord 类型验证**：
  - errors 都是 ErrorRecord 实例
  - 每个 ErrorRecord 含 code/message/details
- **端到端成功路径**：
  - text 完整流程：parse → chunk → validate → write JSON
  - JSON 可解析，含 document_id 和 elements
  - output_path=None 时 Document 仍返回

### 撞墙记录
1. test_validate_only_returns_tuple_of_bool_str：fixture tmp_path 未注入
   （缺参数）。修复：函数加 tmp_path 参数。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 140 后）：11031 pass / 0 fail / 13 skip（HEAD `98ed403`）

### 下一步建议
- 候选 GX：app/cli.py 第六轮
- 候选 GY：app/schema.py 第五轮（深度 if/then 分支）
- 候选 GZ：app/models.py 第五轮
- 候选 HA：app/hash.py 第四轮
- 候选 HB：app/parsers/text_parser.py 第四轮
- 候选 HC：app/parsers/base.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GY（app/schema.py 第五轮）。schema 是 Document 校验核心，
第五轮可深入 if/then 分支（pdf vs docx）、bbox 校验、enum 值、source_locator
结构。

---

## Round 141（2026-08-05）：app/schema.py 第五轮（edges4）

### 目标
- 给 app/schema.py（93 行，已有 464 测试）补第五轮 edges
- 深入 SchemaValidationError / load_schema / validate 错误聚合 / validate_file

### 改动
- 新增 `tests/test_schema_edges4.py`（72 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMA_PATH 常量**：
  - Path 类型
  - 名字 = document.schema.json
  - 文件存在
  - 绝对路径（resolve）
- **SchemaValidationError 类**：
  - message 透传
  - errors 默认空 list
  - None errors → 空 list
  - 显式 errors 透传
  - 是 Exception 子类
  - args 包含 message
  - __init__ 3 参数
- **load_schema 深度**：
  - 默认从 SCHEMA_PATH 加载
  - str/Path 都接受
  - missing file → FileNotFoundError
  - invalid JSON → JSONDecodeError
  - empty file → JSONDecodeError
  - 返回 dict 含 properties
- **validate 错误聚合**：
  - 单错误 → errors 含 1 项
  - 多错误 → 全部收集（3 项）
  - 每个 error 含 path/message/schema_path
  - 异常 message 含 "(N 处)"
  - 用 errors[0] 的 message
  - schema=None → 用默认 SCHEMA_PATH
  - 空 schema dict 接受任何输入
- **is_valid 深度**：
  - True/False 路径
  - 无 schema → 用默认
  - 返回 bool 类型
  - 不抛异常（吞 SchemaValidationError）
- **validate_file 深度**：
  - missing file → FileNotFoundError + "不存在"
  - invalid JSON → JSONDecodeError
  - empty file → JSONDecodeError
  - 显式 schema 工作
  - str 路径也工作
- **模块结构**：
  - __all__ 6 项（SCHEMA_PATH/SchemaValidationError/load_schema/validate/is_valid/validate_file）
  - imports 完整（json/Path/Any/Draft202012Validator/JSValidationError）
  - from __future__ import annotations
  - docstring 提及 JSON Schema
  - _silence_unused_import helper 存在 + 返回 None
- **签名深度**：
  - load_schema 1 参（path 默认 SCHEMA_PATH）
  - validate 2 参（document 必填，schema 默认 None）
  - is_valid 2 参（同上）
  - validate_file 2 参（path 必填，schema 默认 None）
  - SchemaValidationError.__init__ 3 参
- **不变量**：
  - validate vs is_valid 一致
  - 不修改输入

### 撞墙记录
1. test_validate_return_annotation_none：from __future__ 使注解为 'None'
   字符串。修复：assert in (None, "None", empty)。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 141 后）：11103 pass / 0 fail / 13 skip（HEAD `c73f962`）

### 下一步建议
- 候选 GZ：app/models.py 第五轮
- 候选 HA：app/hash.py 第四轮
- 候选 HB：app/parsers/text_parser.py 第四轮
- 候选 HC：app/parsers/base.py 第四轮
- 候选 HD：app/parsers/kreuzberg_parser.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 GZ（app/models.py 第五轮）。models 是数据类核心，第五轮
可深入 Document/Element/Chunk/Relation 数据类 to_dict/from_dict、
WarningRecord/ErrorRecord 字段验证。

---

## Round 142（2026-08-05）：app/models.py 第五轮（edges4）

### 目标
- 给 app/models.py（154 行，已有 307 测试）补第五轮 edges
- 深入 dataclass 字段顺序、默认值独立性、to_dict 行为、__post_init__ 边界

### 改动
- 新增 `tests/test_models_edges4.py`（76 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMA_VERSION 常量**：str，值 "0.1.0"
- **ElementType/SourceType**：
  - 8 个 element type
  - 6 个 source type
- **Element __post_init__**：
  - empty id raises ValueError
  - content+resource 都给 OK
  - content-only / resource-only OK
  - empty content string 视为 falsy
  - 默认 confidence=1.0
  - default_factory metadata 独立 per instance
- **Element 字段顺序**：element_id/type/source_locator/parent_id/content/resource_path/confidence/metadata
- **Chunk __post_init__**：
  - empty id raises
  - empty text raises
  - empty source_ids raises
  - 默认 metadata/source_spans 独立
- **Chunk 字段顺序**：chunk_id/text/source_element_ids/metadata/source_spans
- **Relation**：4 字段，默认 metadata 独立
- **WarningRecord/ErrorRecord**：
  - to_dict 默认 details=None 时不出现
  - 字段顺序 code/reason/details 或 code/message/details
- **Document**：
  - to_dict 13 个键（schema_version + 12 字段）
  - 所有 list 字段递归序列化
  - 默认 metadata 独立
  - 12 个字段顺序
- **dataclass 验证**：6 个类都是 dataclass
- **模块结构**：
  - 无 __all__（公开 API 通过属性访问）
  - imports dataclasses/typing
  - from __future__ import annotations
  - docstring 提及 dataclass
- **签名深度**：所有 to_dict 都是 1 参（self）
- **JSON 序列化**：Element/Chunk/Document 都可 json.dumps
- **综合**：所有可选字段填充的完整实例

### 撞墙记录
1. app/models.py 无 __all__ 属性，但测试试图 import __all__ → ImportError。
   修复：删除 __all__ 测试，改为验证模块无 __all__。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 142 后）：11179 pass / 0 fail / 13 skip（HEAD `7ec0525`）

### 下一步建议
- 候选 HA：app/hash.py 第四轮
- 候选 HB：app/parsers/text_parser.py 第四轮
- 候选 HC：app/parsers/base.py 第四轮
- 候选 HD：app/parsers/kreuzberg_parser.py 第四轮
- 候选 HE：evaluation/__init__.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HA（app/hash.py 第四轮）。hash 是简单但关键的模块，第四轮
可深入 SHA256 校验、文件 IO 边界、compute_text_hash 等。

---

## Round 143（2026-08-05）：app/hash.py 第四轮（edges3）

### 目标
- 给 app/hash.py（24 行，已有 157 测试）补第四轮 edges
- 深入 SHA-256 标准向量、流式读取、跨函数一致性

### 改动
- 新增 `tests/test_hash_edges3.py`（45 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SHA-256 NIST 测试向量**：
  - 空字符串标准 hash
  - 单字符 a
  - "abc" 标准
  - 长测试向量
- **hexdigest 格式**：str、64 字符、小写 hex
- **compute_text_hash 不变量**：
  - 相同输入 → 相同输出
  - 不同输入 → 不同输出
  - Unicode UTF-8 编码
  - 长文本/空白/换行
- **compute_file_hash 深度**：
  - str / Path 都接受
  - 文件 hash = text hash(文件内容)
  - 空文件、单字节、二进制、Unicode
  - 大文件流式（>64KB buffer）
  - 相同内容相同 hash
  - 不同内容不同 hash
- **错误路径**：
  - missing file → FileNotFoundError
  - directory → FileNotFoundError
  - 错误 message 含"不是文件"
- **模块结构**：imports hashlib/Path，future annotations
- **签名**：1 参，无默认，返回 str
- **跨函数一致性**：
  - file hash == hashlib.sha256(content)
  - 多次调用结果稳定

### 撞墙记录
无（hash 模块简单，45 测试全过）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 143 后）：11224 pass / 0 fail / 13 skip（HEAD `e13b3c7`）

### 下一步建议
- 候选 HB：app/parsers/text_parser.py 第四轮
- 候选 HC：app/parsers/base.py 第四轮
- 候选 HD：app/parsers/kreuzberg_parser.py 第四轮
- 候选 HE：evaluation/__init__.py 第四轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HB（app/parsers/text_parser.py 第四轮）。text parser 是最
简单的 parser，第四轮可深入 .txt 读取、空文件、Unicode 编码等。

---

## Round 144（2026-08-05）：app/parsers/text_parser.py 第四轮（edges5）

### 目标
- 给 app/parsers/text_parser.py（136 行，已有 base/edges/edges2/edges3/edges4 共 392 测试）补第五轮
- 深入 _split_paragraphs 算法不变量、TextParser 类属性、parse() 全流程

### 改动
- 新增 `tests/test_parsers_text_edges5.py`（63 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_TEXT_EXTENSIONS 常量**：元组、含 .txt/.text、count=2
- **_detect_text_source_type 深度**：
  - 大小写不敏感（.TXT/.TEXT/.TxT 都识别）
  - 错误 details 含 suffix 字段
  - message 含"(无)"（无后缀时）
- **_split_paragraphs 算法**：
  - 空、单段、多段（一空行分隔）
  - 多空行视为同一段落分隔
  - 首尾空行跳过
  - 仅空行 → []
  - 空白行（含 tab/space）视为空行
  - 连续非空行属同一段落
  - CRLF/CR → LF 归一化
  - 段落 strip、tuple 类型 (int, str)
- **TextParser 类属性**：
  - name="text"、version="stdlib/0.1.0"
  - 继承 Parser
- **parse() 全流程**：
  - 每段一个 element（type=paragraph）
  - element_id 后缀 ::e0000
  - confidence=0.95
  - source_locator={"line":N}
  - metadata={}
  - 空文件 → text_no_content warning
  - 纯空行 → text_no_content warning
  - metadata={"text": True}
  - chunks/relations/errors 默认空列表
- **编码边界**：CRLF 文件、非法 UTF-8 → errors=replace
- **错误路径**：file_not_found、unsupported_type、OSError → text_read_failed
- **模块结构**：__all__=["TextParser"]、imports、docstring
- **签名深度**：helpers 1 参数、parse 3 参数、无默认值
- **综合行为**：
  - 不同 source_hash → 不同 document_id
  - warning.reason 非空
  - 不修改输入文件

### 撞墙记录
无（63 测试全过，0 失败）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 144 后）：11287 pass / 0 fail / 13 skip（HEAD `67ffc20`）

### 下一步建议
- 候选 HC：app/parsers/base.py 第四轮
- 候选 HD：app/parsers/kreuzberg_parser.py 第四轮
- 候选 HE：evaluation/__init__.py 第四轮
- 候选 HF：app/parsers/markdown_parser.py 第六轮
- 候选 HG：app/parsers/html_parser.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HC（app/parsers/base.py 第四轮）。base 是 parser 抽象基类，
第四轮可深入 ParserError 错误码、support 检查、__init__ 子类逻辑等。

---

## Round 145（2026-08-05）：app/parsers/base.py 第四轮（edges3）

### 目标
- 给 app/parsers/base.py（95 行，已有 base/edges/edges2 共 265 测试）补第四轮
- 深入签名、ParserError pickle/copy 行为、Parser 抽象类内部、极端输入

### 改动
- 新增 `tests/test_parsers_base_edges3.py`（118 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **签名深度**：
  - ParserError.__init__ 4 参（self/code/message/details），details 默认 None
  - make_document_id 1 参（source_hash），返回 str
  - detect_source_type 1 参（path），返回 SourceType
  - Parser.parse 3 参（self/path/source_hash），无默认值
  - _silence_unused 0 参
  - from __future__ → 字符串注解（'None'、'SourceType'、'str'）
- **ParserError 复杂场景**：
  - 关键字参数 / 混合位置 / 仅必填位置
  - pickle.dumps 成功但 pickle.loads 失败（args 仅含 message）
  - copy.copy / deepcopy 失败（同上原因）
  - hashable、hash 稳定、可作 dict key
  - except 块内 raise 保留 __context__
  - Unicode message、args 含 Unicode
  - 修改 details 不影响其他实例默认值
- **Parser 抽象类内部**：
  - __abstractmethods__ 含 'parse'、count=1
  - __isabstractmethod__ True
  - 直接子类未实现 parse 仍抽象
  - 子类实现 parse 清除抽象标记
  - 子类 super().parse() 抛 NotImplementedError
  - 类属性 name/version 类级访问
  - 继承 ABCMeta、无自定义 __init__
  - 实例 __dict__ 独立、无实例属性时为空
- **make_document_id 极端输入**：
  - 全 0、全 f、混合 hex
  - bytes 长度 64 → 不抛（格式化 bytes 切片）
  - None/int → TypeError 或 AttributeError
  - 第 17 字符及之后不影响结果
  - 63/65/空 → ValueError 含 'source_hash'
- **detect_source_type 极端**：
  - 文件名含空格、多嵌套目录
  - '.pdf' 单独作为路径 → suffix='' → raise
  - 大写 .PDF → lower 后识别为 'pdf'
  - None/bytes/int → TypeError/AttributeError
  - 'file.pdf?query=val' → raise
  - 错误 details suffix 含 '.pdff'/'.docxx' 等
- **_silence_unused**：docstring 含 Literal/SourceType、可多次调用、无副作用
- **模块 dunder**：__doc__/__file__/__name__、imports、__all__ 4 项
- **综合行为**：raise from 链、集中捕获、details 引用共享

### 撞墙记录
- **Wall 1**：pickle.dumps(e) 不抛，但 pickle.loads(e) 失败（Exception 基类 __reduce_ex__ 用 args=("m1",)，__init__ 缺 code）。修复：分开测 dumps 成功、loads 失败。
- **Wall 2**：copy.copy/deepcopy 同样基于 __reduce_ex__，抛 TypeError。修复：改为 expect TypeError。
- **Wall 3**：make_document_id 接受 bytes 不抛（bytes 长度 64 通过、切片格式化为 "doc-b'\\x00...'"）。修复：删除该 raises 测试，改为 accepts 测试。
- **Wall 4**：detect_source_type('.pdf') → Path('.pdf').suffix == '' → raise（不是返回 'pdf'）。修复：改为 expect ParserError。
- **Wall 5**：detect_source_type('file.PDF') → lower 后 .pdf → 识别成功（不 raise）。修复：删除误测，仅保留识别成功测试。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 145 后）：11405 pass / 0 fail / 13 skip（HEAD `935e56d`）

### 下一步建议
- 候选 HD：app/parsers/kreuzberg_parser.py 第四轮
- 候选 HE：evaluation/__init__.py 第四轮
- 候选 HF：app/parsers/markdown_parser.py 第六轮
- 候选 HG：app/parsers/html_parser.py 第六轮
- 候选 HH：app/chunker.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HD（app/parsers/kreuzberg_parser.py 第四轮）。kreuzberg 是可选
parser 适配器，第四轮可深入 kreuzberg 调用、_kreuzberg_elements_to_document
转换、错误路径等。

---

## Round 146（2026-08-05）：app/parsers/kreuzberg_parser.py 第六轮（edges5）

### 目标
- 给 app/parsers/kreuzberg_parser.py（246 行，已有 base/edges/edges2/edges3/edges4 共 599 测试）补第六轮
- 深入 _HEADING_RE/_SHORT_LINE_MAX/_classify_line/_split_content_to_elements/_make_locator

### 改动
- 新增 `tests/test_parsers_kreuzberg_edges5.py`（128 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_HEADING_RE 模式深度**：
  - pattern 是 re.Pattern 对象、含 #{1,6}
  - ^/$ 锚定、无 MULTILINE/IGNORECASE/VERBOSE
  - capture group count
- **_SHORT_LINE_MAX**：=80、int、正数
- **_classify_line 罕见边界**：
  - 单字符、80/81 字符边界、emoji、纯数字、CJK 混排
  - tab、dash、pipe 开头
  - short with period in middle、level 0/1/6
- **_make_locator 边界**：
  - pdf/docx/其他 source_type（else 分支）
  - 负数 paragraph_index、0、999
  - keys 集合、placeholder/heuristic True、signature
- **_split_content_to_elements 复杂场景**：
  - 2-tuple、second 始终空 list
  - empty/whitespace only → 空 elements
  - atx heading + body 同 block → 两 elements
  - confidence 0.6/0.5、kreuzberg_heuristic metadata
  - element_ids 0-padded、unique、递增
  - CRLF/CR、多空行视为单分隔
  - paragraph_index 递增、pdf 用 page=1
- **KreuzbergParser 类属性**：
  - name/version 在 class __dict__
  - __init__ keyword-only、default True、返回 'None' 字符串
  - parse 3 参、无默认、返回 'Document' 字符串
- **模块结构**：__all__、imports、docstring
- **_KREUZBERG_AVAILABLE/_VERSION**：类型检查
- **综合行为**：classify/split 一致性、locator 稳定、实例独立

### 撞墙记录
- **Wall 1**：_HEADING_RE.match('# h1\n# h2') 返回 None（pattern $ 不能在中间换行处匹配且后续还有内容）。修复：改为测试 '# h1' 单行匹配 + '# h1\nextra' 不匹配。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 146 后）：11533 pass / 0 fail / 13 skip（HEAD `36624c3`）

### 下一步建议
- 候选 HE：evaluation/__init__.py 第四轮
- 候选 HF：app/parsers/markdown_parser.py 第六轮
- 候选 HG：app/parsers/html_parser.py 第六轮
- 候选 HH：app/chunker.py 第六轮
- 候选 HI：app/parsers/ipynb_parser.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HE（evaluation/__init__.py 第四轮）。evaluation/__init__.py 是
评测包入口，第四轮可深入 __all__、版本常量、公共 re-exports 等。

---

## Round 147（2026-08-05）：evaluation/__init__.py 第一轮（edges）

### 目标
- 给 evaluation/__init__.py（29 行，已有 test_packages_init.py 17 个 evaluation init 测试）补一轮专用 edges
- 深入版本常量值/格式/关系、__all__ 顺序、docstring 内容、模块结构、reload 稳定性

### 改动
- 新增 `tests/test_evaluation_init_edges.py`（69 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **版本常量具体值**：EVALUATOR/REPORT=1.1, ANNOTATION/MANIFEST=1.0
- **版本格式**：X.Y 数字 regex 匹配
- **版本关系**：
  - evaluator==report, annotation==manifest
  - evaluator != annotation
  - 去重后两值 {1.1, 1.0}
- **__all__ 深度**：
  - list 类型、length 4
  - 顺序：EVALUATOR/REPORT/ANNOTATION/MANIFEST
  - no duplicates
- **Docstring 内容**：
  - 含"评测"、"设计原则"、"app"、"parser/chunker/pipeline"
  - 含"null + reason"、"分母为 0"、"total"、"not_instrumented"
  - 含"版本历史"、"v1.0"、"v1.1"、"text_preservation"、"不可横向比较"
- **模块结构**：
  - __name__/__file__ 验证
  - docstring 长度 > 200
  - 无 class / def / import 语句（纯常量）
  - 4 个顶层大写常量赋值
- **一致性**：report/manifest 子模块引用同一常量
- **Reload 稳定性**：版本号、__all__、docstring 都不变
- **from import 与 import 一致**：常量是同一对象
- **综合行为**：tuple/dict 形式、版本字符串拼接 "1.11.11.01.0"

### 撞墙记录
无（69 测试全过）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 147 后）：11602 pass / 0 fail / 13 skip（HEAD `afdafc2`）

### 下一步建议
- 候选 HF：app/parsers/markdown_parser.py 第六轮
- 候选 HG：app/parsers/html_parser.py 第六轮
- 候选 HH：app/chunker.py 第六轮
- 候选 HI：app/parsers/ipynb_parser.py 第六轮
- 候选 HJ：app/parsers/fallback_parser.py 第三轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HJ（app/parsers/fallback_parser.py 第三轮）。fallback parser
是默认 parser，第三轮可深入 PDF/DOCX 分支、元素构造、warning 细节等。

---

## Round 148（2026-08-05）：app/hash.py 第五轮（edges4）

### 目标
- 给 app/hash.py（24 行，已有 base/edges/edges2/edges3 共 202 测试）补第五轮
- 深入 65536 buffer 边界、函数属性、模块结构

### 改动
- 新增 `tests/test_hash_edges4.py`（64 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **65536 buffer 边界**：65535/65536/65537/131072/196607/655360 字节精确切片
- **SHA-256 测试向量**：重复模式、特殊字符、emoji、4-byte UTF-8、null byte、BOM、1MB
- **函数属性**：__name__/__qualname__/__module__、callable、docstring
- **模块结构**：__doc__/__name__/__file__、无 __all__、imports、future annotations
- **顶层 def 仅 2 个**：compute_file_hash / compute_text_hash
- **签名深度**：POSITIONAL_OR_KEYWORD kind、no varargs
- **文件路径形式**：relative、dots、double-dot parent、forward slash
- **错误消息**：含路径名、FileNotFoundError 是 OSError 子类
- **跨函数一致性**：多文件 / 多字符串与 hashlib 对比
- **不变量**：idempotent、不修改输入、不修改文件 mtime
- **综合行为**：file_hash 与 text_hash 同 length / charset / lowercase

### 撞墙记录
- **Wall 1**：compute_file_hash.__doc__ 是中文（"流式读取..."），不含 "SHA"/"hash" 英文关键词。修复：改为测中文 "流式"/"摘要" 或英文 "hash"。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 148 后）：11666 pass / 0 fail / 13 skip（HEAD `0b2f905`）

### 下一步建议
- 候选 HK：app/models.py 第六轮
- 候选 HL：app/schema.py 第六轮
- 候选 HM：app/pipeline.py 第六轮
- 候选 HN：evaluation/runner.py 第六轮
- 候选 HO：evaluation/metrics.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HK（app/models.py 第六轮）。models 是核心数据类，
第六轮可深入 dataclass 字段、to_dict 序列化、__post_init__ 边界。

---

## Round 149（2026-08-05）：app/models.py 第六轮（edges5）

### 目标
- 给 app/models.py（154 行，已有 base/edges/edges2/edges3/edges4 共 383 测试）补第六轮
- 深入模块结构、Element/Chunk/Relation 特殊值、asdict 行为、round-trip

### 改动
- 新增 `tests/test_models_edges5.py`（91 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：imports asdict/field/Optional/Literal/Any、无 __all__、6 个 @dataclass
- **SCHEMA_VERSION**：0.1.0 X.Y.Z 格式
- **ElementType/SourceType**：Literal、count 8/6
- **Element 特殊值**：
  - resource_path="" 与 content="" 都 falsy → raise
  - 空白 content/resource_path truthy → OK
  - confidence int 0/1、float 0.0/1.0
  - metadata 嵌套/list/int/None/bool
  - source_locator 空 dict OK、多 key OK
  - parent_id 默认 None / 显式值
  - to_dict 每次新 dict、metadata 修改无回流
- **Chunk 特殊值**：
  - 空白 text truthy → OK（不 raise）
  - source_element_ids=[""] OK
  - metadata 嵌套、source_spans 复杂结构
- **Relation 特殊值**：
  - type/from_id/to_id="" 都 OK
  - metadata 嵌套、to_dict 不共享
- **WarningRecord vs ErrorRecord 对比**：
  - 字段名 reason vs message
  - to_dict 字段集差异
  - details=None 省略、details={} 保留
- **Document 特殊值**：
  - document_id/source_path/source_hash="" 都 OK（无 __post_init__）
  - to_dict 用同一引用（不复制 metadata）
  - elements/metadata default_factory 跨实例独立
- **asdict 对比**：to_dict == asdict
- **round-trip**：to_dict → 构造器 → 等价
- **dataclass 字段默认值类型**
- **综合行为**：6 个 dataclass 都有 to_dict、相同参数相等、不同参数不等

### 撞墙记录
- **Wall 1**：Chunk text=" " 是 truthy 字符串，`if not self.text` 不拦截。修复：改为不 raise 测试。
- **Wall 2**：Document.to_dict 用 self.metadata 直接引用（不复制）。修复：改为 is 同一引用测试。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 149 后）：11757 pass / 0 fail / 13 skip（HEAD `abd57be`）

### 下一步建议
- 候选 HL：app/schema.py 第六轮
- 候选 HM：app/pipeline.py 第六轮
- 候选 HN：evaluation/runner.py 第六轮
- 候选 HO：evaluation/metrics.py 第六轮
- 候选 HP：evaluation/report.py 第六轮
- 候选 HQ：evaluation/manifest.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HL（app/schema.py 第六轮）。schema 模块是 JSON Schema 校验核心，
第六轮可深入 SchemaValidationError、load_schema、validate 多错误聚合等。

---

## Round 150（2026-08-05）：app/schema.py 第六轮（edges5）

### 目标
- 给 app/schema.py（93 行，已有 base/edges/edges2/edges3/edges4 共 536 测试）补第六轮
- 深入 SCHEMA_PATH 精确性、SchemaValidationError 边界、validate 错误聚合细节

### 改动
- 新增 `tests/test_schema_edges5.py`（82 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMA_PATH**：parent 链、与 app/ 同级、stem/suffix
- **SchemaValidationError 边界**：
  - empty message、special chars、Unicode、newline
  - args length 1、errors default [] / explicit [] / None → []
  - errors 共享引用、is Exception 子类、非 ValueError 子类
- **load_schema 深度**：
  - 默认与显式 SCHEMA_PATH 等价
  - 路径含 .. 段、最小 {} schema、嵌套 schema、array/string/integer root
  - directory → FileNotFoundError
- **validate 错误聚合**：
  - path 空/字段/嵌套/数组索引
  - message 是 str、schema_path 是 list
  - errors count 与 iter_errors 一致
  - exception message 含 "Schema 校验失败" + "N 处"
  - empty schema 接受任何输入、不修改 schema/document
- **is_valid 异常吞咽**：仅 catch SchemaValidationError、返回 bool
- **validate_file 错误优先级**：FileNotFoundError > JSONDecodeError > SchemaValidationError
- **Draft202012Validator**：默认 schema 兼容 Draft 2020-12、check_schema 不抛
- **模块结构 / 签名深度**
- **综合行为**：validate/is_valid 一致、error count 与 message 一致

### 撞墙记录
无（82 测试全过）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 150 后）：11839 pass / 0 fail / 13 skip（HEAD `17f9620`）

### 下一步建议
- 候选 HM：app/pipeline.py 第六轮
- 候选 HN：evaluation/runner.py 第六轮
- 候选 HO：evaluation/metrics.py 第六轮
- 候选 HP：evaluation/report.py 第六轮
- 候选 HQ：evaluation/manifest.py 第六轮
- 候选 HR：app/cli.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HM（app/pipeline.py 第六轮）。pipeline 是核心业务流，
第六轮可深入 get_parser、image_output_dir_for、process_single、validate_only。

---

## Round 151（2026-08-05）：app/pipeline.py 第六轮（edges6）

### 目标
- 给 app/pipeline.py（216 行，已有 edges/errors/helpers/edges2-5 共 524 测试）补第六轮
- 深入 get_parser 具体类型、image_output_dir_for 边界、process_single 错误结构

### 改动
- 新增 `tests/test_pipeline_edges6.py`（94 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_parser 各 parser 具体类型**：
  - FallbackParser/KreuzbergParser/MarkdownParser/HtmlParser/TextParser/IpynbParser
  - 都是 Parser 子类、有 name/version/parse callable
  - 每次返回新实例
  - unknown/empty/uppercase/whitespace name → ValueError
- **image_output_dir_for 边界**：
  - None/Path/str 输入
  - 第一 16 字符、images- 前缀
  - 不同 hash/output_path → 不同 dir
  - 父目录继承、empty string hash OK、empty string output OK
  - 无默认值（output_path 必填）
- **process_single 错误结构**：
  - missing file → file_not_found + details.path
  - unknown parser → unexpected_parser_error + details.parser_name
  - errors 都是 ErrorRecord 实例
  - text parser success → Document with source_hash/document_id/chunks
  - 不写盘时不创建文件、创建嵌套父目录
- **validate_only 各种 JSON 形式**：
  - missing/invalid/empty/schema-fail 都 False
  - 返回 (bool, str) tuple
- **模块结构**：__all__ 4 项、imports 完整、docstring
- **签名深度**：
  - process_single 5 参、parser_name/max_chars/write_json 是 keyword-only
  - validate_only 1 参、json_path 必填
- **综合行为**：process_single → validate_only roundtrip

### 撞墙记录
- **Wall 1**：image_output_dir_for 的 output_path 无 default（必填），不是 None。修复：改为 inspect.Parameter.empty。
- **Wall 2**：test_process_single_returns_tuple 缺 tmp_path fixture 参数。修复：补上。
- **Wall 3**：validate_only('"hello"') 用默认 schema 校验，返回 False（不是合法 document）。修复：改测试为 False 期望。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 151 后）：11933 pass / 0 fail / 13 skip（HEAD `ba293ff`）

### 下一步建议
- 候选 HN：evaluation/runner.py 第六轮
- 候选 HO：evaluation/metrics.py 第六轮
- 候选 HP：evaluation/report.py 第六轮
- 候选 HQ：evaluation/manifest.py 第六轮
- 候选 HR：app/cli.py 第七轮
- 候选 HS：evaluation/cli.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HN（evaluation/runner.py 第六轮）。runner 是评测执行核心，
第六轮可深入 run_pilot、单个文件评测、计时、报告装配等。

---

## Round 152（2026-08-05）：evaluation/runner.py 第六轮（edges6）

### 目标
- 给 evaluation/runner.py（227 行，已有 base/edges/edges2-5 共 501 测试）补第六轮
- 深入 run_evaluation report 顶层结构、_process_one 签名、_load_annotation 边界

### 改动
- 新增 `tests/test_evaluation_runner_edges6.py`（68 测试）
- 仅测试，不动业务代码（仍守 "评测只调用，不改算法"）

### 覆盖要点
- **_load_annotation 边界补强**：
  - UTF-8 BOM → json.load(encoding=utf-8) 不剥离 BOM → JSONDecodeError → None
  - array root、嵌套 dict+array、不修改原文件、不抛异常（invalid/missing）
  - 幂等、每次返回新 dict（不共享引用）
  - 签名：path 必填、return dict|None
- **_process_one 签名**：4 参（doc/output_root/parser_name/max_chars）、无默认、返回 tuple
- **run_evaluation 签名**：
  - parser_name/max_chars/tolerance_chars 是 keyword-only
  - parser_name 默认 "fallback"、max_chars 默认 800、tolerance_chars 默认 30
  - manifest/output_path 必填、return dict
- **模块结构**：
  - __all__ == ["run_evaluation"]
  - imports：json/time/Path/Any/process_single/image_output_dir_for/REPORT_VERSION
  - imports：chunk_boundary_prf/figure_caption_prf/compute_automatic_metrics/aggregate_summary/build_devset_section/build_provenance
  - docstring 提及 total / not_instrumented
  - 无 _silence_unused 函数
  - from __future__ import annotations
- **run_evaluation 端到端**（用 _FakeManifest/_FakeDocEntry 模拟）：
  - 返回 dict、写盘、JSON 可反序列化
  - 顶层 keys：report_version/provenance/devset/summary/per_doc/expected_failures
  - report_version == REPORT_VERSION
  - provenance.parser_name / max_chars
  - devset.status / file_count
  - per_doc[0]：doc_id/metrics/wall_time_seconds
  - wall_time_seconds.parse/chunk 是 None、parse_reason/chunk_reason == "not_instrumented"
  - wall_time_seconds.total 是非负 float
  - expected_failures 空列表（fake manifest 无 expected_failures）
  - 创建嵌套父目录
  - summary 含 counts/success_rates/ratio_macro_averages/silent_drop_total
  - 返回 dict 与落盘 JSON 一致
- **综合行为**：_load_annotation 幂等、每次新 dict

### 撞墙记录
- **Wall 1**：UTF-8 BOM 测试期望解析成功，实际 json.load(encoding=utf-8) 不剥 BOM
  → JSONDecodeError → 返回 None。修复：改为期望 None（与实际行为一致，不改源码）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 152 后）：12001 pass / 0 fail / 13 skip（HEAD `7313394`）

### 下一步建议
- 候选 HO：evaluation/metrics.py 第六轮
- 候选 HP：evaluation/report.py 第六轮
- 候选 HQ：evaluation/manifest.py 第六轮
- 候选 HR：app/cli.py 第七轮
- 候选 HS：evaluation/cli.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HP（evaluation/report.py 第六轮）。report.py 是评测报告装配核心，
第六轮可深入 aggregate_summary/build_devset_section/build_provenance/序列化等。

---

## Round 153（2026-08-05）：evaluation/report.py 第六轮（edges5）

### 目标
- 给 evaluation/report.py（200 行，已有 base/edges/edges2-4 共 475 测试）补第六轮
- 深入常量精确性、aggregate_summary 边界、build_provenance 边界、各函数返回结构

### 改动
- 新增 `tests/test_evaluation_report_edges5.py`（101 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量精确性**：
  - _RATIO_METRICS 12 项（schema_valid/pdf_locator_valid_ratio/docx_locator_valid_ratio/
    image_resource_exists_ratio/chunk_reference_intact_ratio/text_preservation_equal/
    text_char_multiset_precision/text_char_multiset_recall/heading_boundary_compliance/
    chunk_boundary_precision/chunk_boundary_recall/chunk_boundary_f1）
  - figure_caption_* 不在 _RATIO_METRICS（始终 null）
  - _COUNT_METRICS = ("element_count_total",)
  - _SUCCESS_BOOL_METRICS = ("pipeline_success",)
  - 全是 tuple、无重复
- **aggregate_summary 深度**：
  - 空 list → sum=None / rate=None / silent_drop_total=None / all macro_average=None
  - value=0 参与（不算 None）
  - value=None 跳过
  - missing key 跳过
  - success_rate = success_count / total（missing key 仍计入 total）
  - ratio macro average：单值/混合/None 跳过
  - silent_drop_count：sum + None 跳过 + 0 参与
  - 4 个顶层 key（counts/success_rates/ratio_macro_averages/silent_drop_total）
  - 不混 "composite_score"（不混合类型）
  - ratio_macro_averages 含全部 12 个 _RATIO_METRICS key
  - 不修改输入、幂等
- **build_provenance 深度**：
  - max_chars：float 转 int、负值、零、数字字符串
  - parser_name 空串/特殊字符
  - parser_version None/空串
  - dependencies 含 3 个 key（pdfplumber/python-docx/pypdfium2）
  - run_timestamp_iso 可解析、有时区偏移
  - evaluator_version/report_version 与常量一致
  - 9 个顶层 key 精确
  - 每次返回新 dict、JSON 可序列化
- **get_dependency_versions**：3 keys 精确、pdfplumber 非 None、值 str 或 None、新 dict 每次调用
- **get_git_provenance**：worktree 中 commit 是 40 hex chars、非 git 目录 commit=None dirty=False
- **build_devset_section**：6 keys 精确、值透传、categories_covered 共享引用、新 dict 每次调用
- **模块结构**：__all__ 5 项精确、imports 完整、docstring 提及 "聚合"/"不混合"、无 _silence_unused
- **签名深度**：各函数参数名、无默认值、dict 返回类型注解
- **综合行为**：idempotent、不修改输入、可独立组合

### 撞墙记录
- **Wall 1**：非 git 目录测试期望 dirty=True，实际 git status --porcelain 返回非零，
  bool(False and ...) = False（dirty 默认 True 仅在 except 分支）。修复：改期望为 False。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 153 后）：12102 pass / 0 fail / 13 skip（HEAD `35758a7`）

### 下一步建议
- 候选 HQ：evaluation/manifest.py 第六轮
- 候选 HR：app/cli.py 第七轮
- 候选 HS：evaluation/cli.py 第六轮
- 候选 HT：evaluation/metrics.py 第六轮
- 候选 HU：evaluation/annotation_metrics.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HQ（evaluation/manifest.py 第六轮）。manifest.py 是 manifest 加载/校验核心，
第六轮可深入 DocumentEntry/Manifest 类、路径解析、expected_failures 等。

---

## Round 154（2026-08-05）：evaluation/manifest.py 第六轮（edges6）

### 目标
- 给 evaluation/manifest.py（239 行，已有 base/edges/edges2-5 共 665 测试）补第六轮
- 深入 frozen dataclass 行为、_is_absolute_like 边界、content_group_count 配对组合、load_manifest 端到端

### 改动
- 新增 `tests/test_evaluation_manifest_edges6.py`（130 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like 边界**：
  - 空串、单字符、两字符 → False
  - POSIX 绝对（/x）、Windows 盘符大小写、Windows 正斜杠、纯 / → True
  - Windows 盘符无分隔符（C:foo）→ False
  - 数字开头的"盘符"（1:/foo）→ False
- **_has_backslash 边界**：
  - 空、单、多、首/尾 backslash → 正确检测
- **ManifestError**：Exception 子类、非 ValueError 子类、message 保持、空 message、args
- **DocumentEntry frozen dataclass**：
  - 10 个字段精确（doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations）
  - frozen → FrozenInstanceError on setattr
  - 可 hash、等值比较、repr 含类名
- **ExpectedFailure frozen dataclass**：
  - 5 个字段精确（doc_id/path_str/resolved_path/expected_error_code/source_type）
  - frozen、可 hash、source_type 可为 None
- **Manifest frozen dataclass**：
  - 5 个字段（manifest_version/devset_status/documents/expected_failures/project_root）
  - file_count/pdf_count/docx_count property 精确
  - content_group_count：空/全 unpaired/全 paired/混合/单向 paired
  - categories_covered：排序去重、空、list 类型
- **_resolve_relative_path**：empty/absolute/backslash/outside-project 错误消息、valid 透传、嵌套子目录、点当前目录
- **_detect_project_root**：file 路径/dir 路径/无 pyproject fallback
- **load_manifest 端到端**：返回 Manifest、devset_status/documents/categories 默认与透传、缺失文件、str 路径、invalid JSON、project_root 自动/手动
- **模块结构**：__all__ 5 项精确、imports 完整、docstring 提及不变量
- **签名深度**：param names、no defaults、return annotations
- **综合行为**：immutability、实例独立、idempotent、roundtrip

### 撞墙记录
- **Wall 1**：DocumentEntry 字段数我数 9，实际 10（漏了 annotation_resolved）。修复：改 10。
- **Wall 2**：devset_status 用 "test" 不在 schema enum（["complete", "incomplete"]）。修复：改 "incomplete"。
- **Wall 3**：source_type 用 "text" 不在 schema documents enum（["pdf", "docx"]）。修复：改 "pdf"。
- **Wall 4**：manifest_version 用 "1.1" 与 schema const "1.0" 冲突。修复：改 "1.0"（MANIFEST_VERSION = "1.0"）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 154 后）：12232 pass / 0 fail / 13 skip（HEAD `0241cda`）

### 下一步建议
- 候选 HR：app/cli.py 第七轮
- 候选 HS：evaluation/cli.py 第六轮
- 候选 HT：evaluation/metrics.py 第六轮
- 候选 HU：evaluation/annotation_metrics.py 第六轮
- 候选 HV：evaluation/schema.py 第六轮
- 候选 HW：evaluation/schema_validation.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HS（evaluation/cli.py 第六轮）。cli.py 是评测命令行入口，
第六轮可深入 argparse 子命令、参数解析、错误处理等。

---

## Round 155（2026-08-05）：evaluation/cli.py 第六轮（edges6）

### 目标
- 给 evaluation/cli.py（243 行，已有 base/edges/edges2-5 共 479 测试）补第六轮
- 深入 _format_metric 边界、main() 错误码路径、_run_inspect_doc 行为

### 改动
- 新增 `tests/test_evaluation_cli_edges6.py`（92 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_format_metric 边界**：
  - None value 无 reason key、empty reason、unicode reason
  - True/False 无 reason（reasons 默认 "ok"）
  - float 0.0/0.5/负数/极大数（4 位小数格式）
  - int 0/负数
  - dict empty/单 item/多 item 排序
  - string value 含 reason
  - name 短/长/36 字符对齐
- **_build_parser 边界**：
  - prog == "evaluation.cli"、description 含"评测"
  - subparsers required=True（无子命令报错）
  - run choices 精确（fallback/kreuzberg，reject others）
  - validate-report/inspect-doc 接受单个 positional
  - inspect-doc tolerance-chars 默认 30 / 自定义
  - 无命令、未知命令、缺必填参数 → SystemExit
  - max-chars 类型 int、非 int 报错、负值
- **main() 错误码路径**：
  - 无 args → SystemExit
  - run 缺 manifest 文件 → 2
  - validate-report 缺文件 → 2、invalid JSON → 1
  - inspect-doc 缺文件 → 2、invalid JSON → 1、array 顶层 → 1、最小 dict → 0
  - inspect-doc 打印 file path、metrics header、"?"
- **_run_inspect_doc 边界**：缺文件/invalid JSON/array/minimal dict/tolerance/elements+chunks
- **模块结构**：无 __all__、imports 完整（含 get_git_provenance）、utf-8 reconfigure、main guard、docstring 含三个子命令
- **签名深度**：main argv 默认 None + int 返回、_build_parser 无参、_format_metric name+metric+str、_run_inspect_doc args+int
- **综合行为**：
  - _format_metric 幂等、不修改输入
  - _build_parser 每次返回新 parser
  - main 端到端 run（mock load_manifest/run_evaluation/validate_file）→ rc=0
  - main 端到端 run（mock 抛 ManifestError）→ rc=1
  - main 端到端 run --parser kreuzberg --max-chars 500 --tolerance-chars 10

### 撞墙记录
- 无（一次跑通）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 155 后）：12324 pass / 0 fail / 13 skip（HEAD `2b25c1f`）

### 下一步建议
- 候选 HT：evaluation/metrics.py 第六轮
- 候选 HU：evaluation/annotation_metrics.py 第六轮
- 候选 HV：evaluation/schema.py 第六轮
- 候选 HW：evaluation/schema_validation.py 第六轮
- 候选 HX：app/cli.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HT（evaluation/metrics.py 第六轮）。metrics.py 是指标计算核心，
第六轮可深入 compute_automatic_metrics 各分支、比例指标分母、reason 字段等。

---

## Round 156（2026-08-05）：evaluation/metrics.py 第六轮（edges6）

### 目标
- 给 evaluation/metrics.py（381 行，已有 base/edges/edges2-5 共 902 测试）补第六轮
- 深入常量精确性、helper 返回结构、_strip_unicode_whitespace Unicode 边界、_is_valid_bbox 边界、各 ratio 子函数、compute_automatic_metrics 端到端

### 改动
- 新增 `tests/test_evaluation_metrics_edges6.py`（145 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量精确性**：
  - _TEXT_TYPES 7 项（heading/paragraph/list_item/table/caption/header/footer），无 image
  - _PDF_BBOX_REQUIRED_TYPES 4 项（heading/paragraph/caption/list_item），是 _TEXT_TYPES 子集，无 table
  - _NOT_EVALUATED == "not_evaluated"
  - 全 tuple、无重复
- **helper 返回结构**：
  - _null/_ratio/_bool_metric/_int_metric 各自 shape
  - _ratio 强制 float、_bool_metric 强制 bool、_int_metric 强制 int
  - 每次返回新 dict
- **_strip_unicode_whitespace 边界**：
  - ASCII 空白（space/tab/newline/cr/vtab/formfeed）
  - Unicode 空白（NBSP/em space/en space/ideographic space/line separator/paragraph separator）
  - 全空白字符串 → 空、不排序、保留 emoji/中文/标点
- **_is_valid_bbox 边界**：None/空/短/长 list、int/float/mixed、bool 拒绝、NaN/inf/-inf 拒绝、string/tuple 拒绝、零值/负值有效
- **_pdf_locator_ratio 边界**：empty、no-bbox 类型 page≥1 即可、heading 缺 bbox 无效、page 0/-1/None 无效
- **_docx_locator_ratio 边界**：含 page/bbox 无效、structural keys（section/paragraph_index/...）、缺失 locator
- **_chunk_reference_ratio 边界**：empty、unknown id、empty/missing/None ids
- **_heading_boundary_ratio 边界**：no headings、no chunks、match first id、heading not first、empty ids
- **_silent_drop_count 边界**：no expectations、empty element_count、matches/exceeds/missing/multiple
- **compute_automatic_metrics 端到端**：
  - pipeline_failed → 14 keys 全 null + reason="pipeline_failed"
  - minimal document (pdf/docx)
  - element_count_by_type aggregation、missing type → "unknown"
  - text_preservation: empty/perfect/extra/missing
  - schema_check_exception → False + exception reason
  - image_resource_ratio 调用子函数
- **模块结构**：__all__ == ["compute_automatic_metrics"]、imports (math/Counter/Path/Any)、docstring 提及"不伪造"/"不返回 1.0"/"text_preservation"
- **签名深度**：5 参 compute_automatic_metrics + 各子函数精确
- **综合行为**：不修改输入、idempotent、helper 独立

### 撞墙记录
- **Wall 1**：__all__ 实际存在（["compute_automatic_metrics"]），不是我假设的"无"。修复：改为精确 list。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 156 后）：12469 pass / 0 fail / 13 skip（HEAD `765653c`）

### 下一步建议
- 候选 HU：evaluation/annotation_metrics.py 第六轮
- 候选 HV：evaluation/schema.py 第六轮
- 候选 HW：evaluation/schema_validation.py 第六轮
- 候选 HX：app/cli.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HU（evaluation/annotation_metrics.py 第六轮）。annotation_metrics.py 是
标注指标核心，第六轮可深入 chunk_boundary_prf 容差匹配、figure_caption_prf 启发式等。

---

## Round 157（2026-08-05）：evaluation/annotation_metrics.py 第六轮（edges6）

### 目标
- 给 evaluation/annotation_metrics.py（194 行，已有 base/edges/edges2-5 共 457 测试）补第六轮
- 深入 chunk_boundary_prf 各分支（document None、empty annotation、chunks<2、anchor 0/多、tolerance 边界、before/after、相同 marker 顺序定位）

### 改动
- 新增 `tests/test_annotation_metrics_edges6.py`（66 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **PARSER_DOES_NOT_EMIT_RELATIONS 常量**：精确值 + str 类型 + 在 __all__
- **figure_caption_prf 深度**：
  - 3 keys 精确（precision/recall/f1）
  - 全 null、相同 reason
  - None document、None annotation、both None、真实 doc、annotation 含 relation
  - 每次返回新 dict、JSON 可序列化
- **chunk_boundary_prf document None 路径**：3 key null + reason="pipeline_failed" + _tolerance_chars
- **chunk_boundary_prf empty annotation**：3 key null + reason="no_annotation"
- **chunk_boundary_prf chunks<2 路径**：
  - 0 chunks + 有 anchors → recall=_ratio(0.0)（anchors 非空走 _ratio）
  - 1 chunk + 0 anchors → recall=no_predicted_boundaries（anchors 空走 null）
  - 1 chunk + 有 anchors → recall=_ratio(0.0)
- **chunk_boundary_prf 完整匹配路径**：
  - 完美匹配（precision/recall/f1 = 1.0）
  - position=before/after
  - tolerance 边界：within match / beyond miss
  - partial match：2 chunks + 2 anchors（marker 不重叠）→ 1 match, p=1, r=1/2
  - multiple chunks + multiple anchors
  - 相同 marker 顺序定位（不都命中第一次）
  - tolerance=0 仅精确匹配、tolerance=-1 永远不匹配
- **_missing_markers 行为**：missing 时添加 key、不 missing 时无 key、空 marker 视为 missing
- **f1 计算**：p 或 r None → f1 null、p+r=0 → f1=0.0
- **不修改输入**：document / annotation 都不修改
- **模块结构**：__all__ 3 项精确、imports (Counter/Any/normalize_text/_null/_ratio)、docstring 提及"启发式"/"一对一"/"tolerance"
- **签名深度**：figure_caption_prf 2 参无默认、chunk_boundary_prf 3 参 tolerance 默认 30
- **综合行为**：idempotent、JSON 可序列化

### 撞墙记录
- **Wall 1**：原期望 0 chunks + 有 anchors 时 recall 是 null，实际 anchors 非空走 `_ratio(0.0)`
  分支（source code 中 `if not anchors else _ratio(0.0)`）。修复：改期望。
- **Wall 2**：1 chunk + 0 anchors 时 recall 走 null 分支（`if not anchors` True）。
  修复：改测试为期望 null。
- **Wall 3**：partial match 测试用了 3 anchors 在同 stream 中，但 search_from 推进逻辑导致
  只有第一个 marker 能找到（后续 marker 在已搜过区域）。修复：改为 2 个不重叠的 marker。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 157 后）：12535 pass / 0 fail / 13 skip（HEAD `8d8260f`）

### 下一步建议
- 候选 HV：evaluation/schema.py 第六轮
- 候选 HW：evaluation/schema_validation.py 第六轮
- 候选 HX：app/cli.py 第七轮
- 候选 HY：app/parsers/markdown_parser.py 第七轮
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HV（evaluation/schema.py 第六轮）。schema.py 是 evaluation 模块的 schema 调度层，
第六轮可深入 validate/validate_file 的 schema_name 调度、错误聚合等。

---

## Round 158（2026-08-05）：evaluation/schema.py 第六轮（edges4）

### 目标
- 给 evaluation/schema.py（80 行，已有 base/edges/edges2/edges3 共 394 测试）补第六轮
- 深入 SCHEMAS_DIR 路径、EvalSchemaError 边界、_schema_path 错误、validate 错误聚合细节

### 改动
- 新增 `tests/test_evaluation_schema_edges4.py`（78 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMAS_DIR 精确性**：absolute/resolved、parent 是项目根、含 4 个已知 schema
- **EvalSchemaError 边界**：empty message、特殊字符、args 长度、None errors → empty list、errors 共享引用、init signature 3 参
- **_schema_path**：返回 Path、unknown raises FileNotFound + 消息、absolute、parent 是 SCHEMAS_DIR
- **load_schema 深度**：返回 dict（manifest/annotation/evaluation-report）、unknown raises、签名
- **validate 错误聚合**：
  - 通过校验返回 None
  - 单错误 path=[]、property 错误 path 含字段
  - error message/schema_path 都是 list
  - errors 长度 == validator.iter_errors 数量
  - 异常消息含 "Schema"/"校验失败"/"X 处"/schema_name
  - 不修改 instance
- **validate_file 错误优先级**：FileNotFound > JSONDecodeError > EvalSchemaError；目录 raises；unknown schema raises
- **Draft202012Validator 兼容性**：manifest/annotation/evaluation-report schema 都通过 check_schema
- **模块结构**：__all__ 5 项精确、imports (json/Path/Any/Draft202012Validator/JSValidationError)、docstring 提及与 app/schema 的分离
- **签名深度**：load_schema/validate/validate_file 参数名、无默认、返回类型注解
- **综合行为**：idempotent load_schema、validate 与直接 validator 一致、EvalSchemaError 捕获可访问 errors、validate_file 跨多 schema

### 撞墙记录
- 无（一次跑通）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 158 后）：12613 pass / 0 fail / 13 skip（HEAD `eccbe99`）

### 下一步建议
- 候选 HW：evaluation/schema_validation.py 第六轮
- 候选 HX：app/cli.py 第七轮
- 候选 HY：app/parsers/markdown_parser.py 第七轮
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HW（evaluation/schema_validation.py 第六轮）。schema_validation.py 是
document_passes_schema 调度层，第六轮可深入 schema 校验、错误聚合等。

---

## Round 159（2026-08-05）：evaluation/schema_validation.py 第三轮（edges3）

### 目标
- 给 evaluation/schema_validation.py（15 行，已有 base/edges/edges2 共 81 测试）补第三轮
- 深入 document_passes_schema 各分支、模块结构（极简）、签名深度

### 改动
- 新增 `tests/test_evaluation_schema_validation_edges3.py`（31 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **document_passes_schema 各分支**：
  - 空 dict / None / str / list / int → False（不抛异常）
  - 返回 bool 类型、bool 化（源码 `return bool(is_valid(...))`）
- **模块结构**：
  - __all__ == ["document_passes_schema"]、单公共名
  - imports Any、future annotations
  - docstring 提及"避免 import 循环"
  - **无 module-level app.schema import**（用延迟 import 避免循环）
  - 函数体内含 `from app.schema import is_valid`
- **签名深度**：1 参 document（dict 注解，无默认），返回 bool
- **综合行为**：idempotent、不修改输入、与 app.schema.is_valid 一致、多类型不抛、含额外 keys 不抛

### 撞墙记录
- 无（一次跑通）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 159 后）：12644 pass / 0 fail / 13 skip（HEAD `1c365fd`）

### 下一步建议
- 候选 HX：app/cli.py 第七轮
- 候选 HY：app/parsers/markdown_parser.py 第七轮
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 候选 IB：app/chunkers/structural.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HX（app/cli.py 第七轮）。cli.py 是文档处理命令行入口，
第七轮可深入 parse/validate 子命令、错误处理、parser 选择等。

---

## Round 160（2026-08-05）：app/cli.py 第七轮（edges6）

### 目标
- 给 app/cli.py（535 行，已有 base/edges/edges2-5 共 624 测试）补第七轮
- 深入 _preview/_load_document_json/_format_summary/_format_elements_list/_format_chunks_list/_iter_supported_files/_relative_output_path/_infer_parser_name/_emit_structured_error

### 改动
- 新增 `tests/test_cli_edges6.py`（123 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_preview 边界**：None/empty/short/边界/超长、换行+连续空白 collapse、unicode、自定义/negative/zero width
- **_load_document_json**：missing file/invalid JSON/empty file/valid dict/array、返回 tuple、str path
- **_format_summary**：empty dict、minimal、full、含 warnings（5 个上限）、errors、elements by type、chunk text/refs stats
- **_format_elements_list**：empty/single/limit 0/limit truncates/missing fields/parent_id
- **_format_chunks_list**：empty/single/show_spans 空/有数据/不显示、limit truncates、missing fields
- **_iter_supported_files**：empty/filter by ext/sorted/recursive/non-recursive skip subdirs/uppercase ext/returns list/skips dirs
- **_relative_output_path**：top-level/nested/deep nested/不同扩展名无冲突
- **_infer_parser_name**：pdf/docx/md/markdown/html/htm/txt/text/ipynb/unknown/no-suffix/uppercase/mixed
- **_EXTENSION_TO_PARSER 常量**：9 keys 精确、pdf+docx 都是 fallback、值都是 str
- **_emit_structured_error**：写到 stderr、含 schema_version/input、code/message、可加 extra fields、JSON 可序列化
- **模块结构**：无 __all__、imports 完整、future annotations、utf-8 reconfigure、main guard、docstring 提及 parse/validate/inspect
- **签名深度**：各函数参数名、默认值（width=60、show_spans=False）、返回类型
- **综合行为**：preview/load/iter/infer/relative_output 都 idempotent

### 撞墙记录
- **Wall 1**：常量名 `_extension_to_parser` 实际是 `_EXTENSION_TO_PARSER`（全大写）。修复：import 与使用都改。
- **Wall 2**：`_preview(width=0)` 时 `len(collapsed) <= 0` 为 False，走 truncation 分支返回 `collapsed[:-1] + '…'`，
  所以 `_preview("hello", width=0) == "hell…"` 而非 `"…"`。修复：改测试期望。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 160 后）：12767 pass / 0 fail / 13 skip（HEAD `afe779c`）

### 下一步建议
- 候选 HY：app/parsers/markdown_parser.py 第七轮
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 候选 IB：app/chunkers/structural.py 第六轮
- 候选 IC：app/parsers/text_parser.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IB（app/chunkers/structural.py 第六轮）。structural.py 是文档分块核心，
第六轮可深入 normalize_text、heading boundary、chunk 算法等。

---

## Round 161（2026-08-05）：app/chunkers/structural.py 第七轮（edges7）

### 目标
- 给 app/chunkers/structural.py（388 行，已有 base/edges/edges2-6 共 792 测试）补第七轮
- 深入 _SplitPiece frozen dataclass、_hard_split_with_whitespace_fallback、_split_long_text、_ChunkBuffer、StructuralChunker.chunk、_element_text_with_span、normalize_text

### 改动
- 新增 `tests/test_chunker_edges7.py`（118 测试）
- 仅测试，不动业务代码（不改 parsers/chunkers/pipeline）

### 覆盖要点
- **常量精确性**：_SENTENCE_SPLIT_RE 编译模式、_HARD_BREAK_LANGS 6 项、_WHITESPACE_RE 模式、_PART_TEXT/ELEMENT_ID/START/END 索引
- **_SplitPiece frozen dataclass**：4 字段精确、frozen 行为（FrozenInstanceError）、必填字段（text/boundary_after）、start/end 默认 0、hashable、相等性、repr 含类名
- **_hard_split_with_whitespace_fallback 深度**：empty/short/exactly-max/long-no-ws（forced_char）/long-with-ws（whitespace）/leading-ws/trailing-ws/only-ws/max_chars=1
- **_split_long_text 深度**：empty/only-ws/shorter-than-max/exactly-max/long-text/multiple-sentences/each-piece-within-max/strip/char-conservation
- **_ChunkBuffer**：init/push_text/length/is_empty/flush、source_ids dedup、首次出现顺序、one-span-per-part、chunk_id 格式 `{doc_id}::c{counter:04d}`、metadata keys（strategy/max_chars/char_count）、keyword-only flush args
- **StructuralChunker**：__init__ default 800、custom、too-small raises ValueError（<32）、boundary 32 OK、zero/negative raises
- **StructuralChunker.chunk 场景**：no elements、single short paragraph、heading creates boundary、table isolated、image skipped、caption isolated、long paragraph split、empty content skipped、chunk_id increments、default sequential strategy
- **_element_text_with_span**：image/empty/none/whitespace-only/strips/no-strip/leading-only/trailing-only
- **模块结构**：__all__ 精确 2 项、imports、docstring 提及 heading/spans/no-text-modification
- **normalize_text edges**：empty/None/no-ws/collapse/strips/mixed/only-ws
- **综合行为**：normalize 幂等、_SplitPiece immutable、flush-then-flush-None 幂等、no-text-loss

### 撞墙记录
- **Wall 1**：`_SplitPiece(text="x")` 失败 — `boundary_after` 也是必填字段（无默认值）。修复：所有构造改为
  `_SplitPiece(text="x", boundary_after=None)`，并把对应"默认值"测试改成"必填字段"测试。
- **Wall 2**：`_make_el("e1", "paragraph", "")` 触发 `Element.__post_init__` 的 ValueError（content+resource_path
  至少一项非空）。修复：`_make_el` 在 content 为空时改用 `resource_path="placeholder"` 让 Element 通过校验。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 161 后）：12885 pass / 0 fail / 13 skip（HEAD `7065bee`）

### 下一步建议
- 候选 HY：app/parsers/markdown_parser.py 第七轮
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HY（app/parsers/markdown_parser.py 第七轮）。markdown_parser 是 fallback 路径外的核心
markdown 处理入口，第七轮可深入 heading 层级、code block、list 等结构。

---

## Round 162（2026-08-05）：app/parsers/markdown_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/markdown_parser.py（326 行，已有 base/edges/edges2-5 共 702 测试）补第六轮
- 深入 _detect_md_source_type details、_rows_to_md/_split_pipe_row 边界、_parse_text section_path 与 fence/blockquote/段落吸收

### 改动
- 新增 `tests/test_parsers_markdown_edges6.py`（129 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_detect_md_source_type**：details 字段精确（suffix==".txt"/""）、message 提及 .md/.markdown 与实际 suffix
- **_MD_EXTENSIONS**：精确 `(".md",".markdown")`、tuple、小写、点开头
- **_rows_to_md**：empty/单行/双行/uneven 补齐/最大列宽/空 cells/Unicode/separator 固定 3 dashes
- **_split_pipe_row**：无 pipe/前后 pipe/连续 pipe/strip cell/empty string
- **_is_pipe_table_start**：i+1>=len/首行非 pipe/colon separator/无 outer pipe
- **MarkdownParser 类属性**：name="markdown"、version="stdlib/0.1.0"、继承 Parser
- **parse() 路径**：不存在 file_not_found、unsupported_type、metadata={"markdown":True}、空文件/thematic-only 触发 md_no_content
- **_parse_text section_path**：弹栈（H1>H2>H3 → H2）、跳级（H1>H3>H2>H3）
- **围栏**：未闭合吸到 EOF、空 code block 触发 md_empty_code_block、language 字段、~~~ 围栏
- **blockquote**：空不产 element、多行合并、strip
- **段落吸收**：被 table/image/blockquote/fenced/atx/thematic/list 各阻断
- **element_id/confidence/locator**：4 位 zero-pad、0.95 默认、line 1-based
- **表格**：row_count/col_count/source metadata、单 header 行、uneven 补齐
- **图片**：alt/url/content=None、inline image 不被独立提取
- **列表**：unordered (-,+,*) / ordered (.,)) 各 marker、marker 字段、各 item 独立
- **模块结构**：__all__、future annotations、imports、docstring 提及 ATX/setext/frontmatter
- **签名深度**：parse/parse_text/detect_md_source_type/rows_to_md/split_pipe_row/is_pipe_table_start

### 撞墙记录
- **Wall 1**：测试函数使用 `tmp_path` 但签名忘了加 `tmp_path: Path`，导致 NameError。修复：脚本批量加。
- **Wall 2**：`make_document_id` 要求 source_hash 长度 64（SHA-256 hex）。修复：所有短 hash 字面量换成 64 字符。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 162 后）：13014 pass / 0 fail / 13 skip（HEAD `3bc0a62`）

### 下一步建议
- 候选 HZ：app/parsers/html_parser.py 第六轮
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback.py 第六轮
- 候选 IE：app/parsers/base.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 HZ（app/parsers/html_parser.py 第六轮）。html_parser 与 markdown_parser 同属 stdlib
解析器家族，第六轮可深入 html.parser HTMLParser 子类、section_path、table 提取等。

---

## Round 163（2026-08-05）：app/parsers/html_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/html_parser.py（446 行，已有 base/edges/edges2-5 共 597 测试）补第六轮
- 深入 _HTMLDocParser SAX 各 handler、跳过栈、嵌套 table、pre/blockquote depth、locator 行为

### 改动
- 新增 `tests/test_parsers_html_edges6.py`（114 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量精确**：_HTML_EXTENSIONS / _HEADING_LEVELS / _SKIP_TAGS 内容、类型、lowercase
- **_detect_html_source_type**：details.suffix 精确、message 提及 .html/.htm
- **_rows_to_md**：empty/单行/双行/uneven/超宽/Unicode/空 cells/separator 固定
- **_HTMLDocParser 初始状态**：document_id/elements/warnings/_cur_*/_list_stack/_pre_depth/_blockquote_depth/_section_*/_table_*/_skip_stack 全部默认值
- **继承 stdlib**：issubclass HTMLParser、convert_charrefs=True
- **SAX handlers**：handle_starttag/endtag/data/startendtag 都存在
- **标题流程**：h1-h6 level metadata、section_path push/pop/弹栈
- **段落/loose text**：whitespace-only ignored、loose text 成 paragraph
- **列表**：ul unordered、ol ordered、marker metadata
- **pre/blockquote**：metadata.kind="preformatted"/"blockquote"、嵌套 depth 计数
- **图片**：src+alt/src only/empty src/无 src 各分支、self-closing img
- **hr/br**：hr 不产 element、br 在 paragraph 内加空格
- **跳过栈**：script/style/head/title/meta/link/noscript 内容被忽略、跳过后 normal text 恢复
- **嵌套 table**：触发 html_nested_table warning
- **空表格**：rows 空 → _rows_to_md 返回 ""，不产 element
- **col_count**：max of all rows
- **HtmlParser.parse()**：file_not_found/unsupported_type/metadata={"html":True}
- **confidence 精确**：heading/paragraph=0.95，table/image=0.9
- **element_id zero-pad**：4 位 zero-padding
- **locator**：line 字段、section_path 在 heading 后含自身、无 heading 时不含
- **char entity**：convert_charrefs 自动转 &amp;/&lt;/&gt;/&#65;
- **模块结构**：__all__、future annotations、imports、docstring 提及 supported tags 与 nested 限制
- **签名深度**：parse/_detect_html_source_type/_rows_to_md 参数与返回

### 撞墙记录
- **Wall 1**：`<script>outer<script>inner</script>still skip</script>` 测试期望 elements 空，
  实际 html.parser 把 `<script>` 内的 `<script>` 当 CDATA 数据，第一个 `</script>` 关闭外层，
  之后 `still skip` 成为 loose paragraph，第二个 `</script>` 是孤儿 endtag 无效。修复：测试期望
  改成"产 1 个 paragraph，content 是 'still skip'"。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 163 后）：13128 pass / 0 fail / 13 skip（HEAD `adf10ff`）

### 下一步建议
- 候选 IA：app/parsers/ipynb_parser.py 第六轮
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback.py 第六轮
- 候选 IE：app/parsers/base.py 第七轮
- 候选 IF：app/parsers/__init__.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IA（app/parsers/ipynb_parser.py 第六轮）。ipynb 是 notebook 格式，
第六轮可深入 code/markdown cell 分离、nbformat v4 字段、source 字段类型等。

---

## Round 164（2026-08-05）：app/parsers/ipynb_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/ipynb_parser.py（227 行，已有 base/edges/edges2-5 共 632 测试）补第六轮
- 深入 _cell_source_to_text 类型分支、_extract_kernel_language 多形态、parse() 错误路径与 metadata

### 改动
- 新增 `tests/test_parsers_ipynb_edges6.py`（112 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_IPYNB_EXTENSIONS**：精确 (".ipynb",) tuple
- **_detect_ipynb_source_type**：details.suffix 精确、message 提及 .ipynb 与实际 suffix
- **_cell_source_to_text**：str/list/None/int/dict、空、混合类型、list of non-str 强转
- **_extract_kernel_language**：kernelspec.language 优先、kernelspec.name fallback、language_info.name fallback、空 metadata、空字段
- **IpynbParser 类属性**：name="ipynb"、version="stdlib/0.1.0"、继承 Parser
- **parse() 错误**：file_not_found（details.path）、unsupported_type、ipynb_invalid_json、ipynb_bad_structure（顶层非 dict/cells 非 list）、ipynb_unsupported_version（nbformat<4，details.nbformat）
- **nbformat 校验**：None 视为合法（不触发 <4 检查）、3/2 触发、4/5 通过
- **cells 容错**：None/missing → []（再触发 ipynb_no_content）
- **cell_type 分支**：markdown（委托 MarkdownParser）、code（kind=code_cell，content strip）、raw（kind=raw_cell，content strip）、unknown（ipynb_unknown_cell_type warning）、missing（默认 unknown）
- **空 cell**：code 空 → ipynb_empty_code_cell warning；raw 空 → 静默 skip
- **非 dict cell**：ipynb_bad_cell warning，details.cell_index
- **element_id**：连续重编号（cross-cell），4 位 zero-pad，共享 doc_id 前缀
- **locator**：cell_index/cell_type/line（markdown line 来自 sub_element）/section_path（markdown 内）
- **markdown cell 子 warning**：md_empty_code_block 被包装加 cell_index 与"cell #N (markdown)"前缀
- **Document.metadata**：ipynb=True、nbformat、nbformat_minor、cell_count、language
- **模块结构**：__all__、future annotations、imports（json/Path/Any/MarkdownParser）、docstring 提及 nbformat/cell types/outputs 丢弃
- **签名深度**：parse/_detect/_cell_source_to_text/_extract_kernel_language

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 164 后）：13240 pass / 0 fail / 13 skip（HEAD `d9d9c32`）

### 下一步建议
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback.py 第六轮
- 候选 IE：app/parsers/base.py 第七轮
- 候选 IF：app/parsers/__init__.py 第六轮
- 候选 IG：app/chunkers/__init__.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IE（app/parsers/base.py 第七轮）。base.py 是 Parser 抽象基类与 ParserError/make_document_id
的所在，第七轮可深入 Parser 接口契约、ParserError 字段、make_document_id 不变量。

---

## Round 165（2026-08-05）：app/parsers/base.py 第四轮（edges4）

### 目标
- 给 app/parsers/base.py（94 行，已有 base/edges/edges2/edges3 共 383 测试）补第四轮
- 深入 ParserError 字段、make_document_id 不变量、detect_source_type 各分支、Parser 抽象类

### 改动
- 新增 `tests/test_parsers_base_edges4.py`（91 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **ParserError 深度**：
  - init 3 参数（code/message/details）、details 默认 None
  - 不传 details → {}；传 None → {}；传 dict → 原 dict
  - args = (message,)（super().__init__(message)）
  - str/repr 格式、code/message 可为空字符串
  - details dict 在多实例间不共享（每个实例独立 {}）
  - details 支持嵌套 dict/list value
  - raise → catch 后属性可读，caught is original
- **make_document_id**：
  - 返回 `doc-{first 16 hex}`，长度 20
  - 64 字符校验：短/长/空 都 raise ValueError
  - 稳定（同输入同输出）、不同输入不同输出
  - 真实 SHA-256 hex 输入验证
- **detect_source_type**：
  - .pdf/.docx 大小写、Path 对象、双扩展名
  - 不支持扩展（.txt/.md/.html/.ipynb）触发 unsupported_type
  - 无扩展名 details.suffix=""
  - message 提及 .pdf/.docx 与实际 suffix
- **Parser 抽象类**：
  - 是 ABC、inspect.isabstract(Parser) 为 True
  - 不能直接实例化（TypeError）
  - __abstractmethods__ 含 "parse"
  - 默认 name="abstract"、version="0.0.0"
  - 子类未实现 parse → 不能实例化
  - 子类未覆盖 name → 继承父类
  - parse.__isabstractmethod__ is True
- **模块结构**：
  - __all__ 精确 4 项
  - imports：ABC/abstractmethod、Path、Any、Literal、Document、SourceType
  - future annotations
  - docstring 提及"业务代码"与"kreuzberg/pdfplumber/python-docx"
  - _silence_unused 存在、可调用、返回 None、no-op
- **签名深度**：所有公共函数参数名、默认值、返回 annotation

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 165 后）：13331 pass / 0 fail / 13 skip（HEAD `c06dd2d`）

### 下一步建议
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback.py 第六轮
- 候选 IF：app/parsers/__init__.py 第六轮
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/parsers/fallback_pdf.py 第六轮
- 候选 II：app/parsers/fallback_docx.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IF（app/parsers/__init__.py 第六轮）。__init__.py 是 parser 工厂的入口，
第六轮可深入 get_parser/discover_parsers/registry 等。

---

## Round 166（2026-08-05）：app/parsers/__init__.py 第六轮（init_edges）

### 目标
- 给 app/parsers/__init__.py（11 行，仅 re-export）补强
- 深入 __all__、重导出 identity、子模块可导入、所有 Parser 子类继承关系

### 改动
- 新增 `tests/test_parsers_init_edges.py`（40 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **__all__ 精确**：3 项 `["Parser", "ParserError", "make_document_id"]`、list、无重复
- **重导出 identity**：pkg.X is base.X（3 个名字都验证）
- **公共 API 类型**：Parser 是 ABC 类、ParserError 是 Exception 子类、make_document_id 可调用
- **子模块可导入**：base/fallback_parser/kreuzberg_parser/markdown_parser/html_parser/ipynb_parser/text_parser
- **Parser 子类继承**：FallbackParser/MarkdownParser/HtmlParser/IpynbParser/TextParser 都 issubclass(Parser)
- **模块结构**：docstring 提及"业务代码"与"依赖注入/工厂"、__future__ annotations、from .base import
- **子包目录**：所有 *.py 文件存在
- **star import**：只导入 __all__ 中的 3 个名字

### 撞墙记录
- **Wall 1**：测试假设 `app.parsers.fallback`，实际文件名是 `fallback_parser.py`。修复：所有 import 改为
  `app.parsers.fallback_parser`。同时发现还有 `kreuzberg_parser.py`（之前未列），补到 dir 测试中。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 166 后）：13371 pass / 0 fail / 13 skip（HEAD `8ed89c5`）

### 下一步建议
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 ID：app/parsers/fallback_parser.py 第六轮
- 候选 IE：app/parsers/kreuzberg_parser.py 第六轮
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/models.py 第八轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 ID（app/parsers/fallback_parser.py 第六轮）。fallback_parser 是默认 parser 路径
（pdfplumber + python-docx），覆盖最多真实场景，第六轮可深入 PDF/DOCX 各自分支、table/caption/image 提取。

---

## Round 167（2026-08-05）：app/parsers/fallback_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/fallback_parser.py（630 行，已有 base/edges/edges2-5 共 730 测试）补第六轮
- 深入纯函数（caption 正则、rows_to_markdown、image_filename、classify_pdf_paragraph、group_words、lines_to_para）

### 改动
- 新增 `tests/test_parsers_fallback_edges6.py`（115 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_CAPTION_RE 正则**：Pattern 对象、IGNORECASE flag、Table/Figure/Fig./表/图 各 prefix、全角数字、各种分隔符（.、/ fullwidth 、/colon/space）、不匹配 normal text
- **_is_caption**：return bool、empty/None 安全、word in middle 不匹配
- **_rows_to_markdown**：None→""、int→str、混合类型、Unicode、uneven 补齐、空 cells
- **_image_filename**：02d zero-pad、ext 切换、doc- 前缀剥离、prefix 参数、index 0/large
- **_classify_pdf_paragraph**：caption 优先、80 char 临界（heading ↔ paragraph）、各种结尾标点（.。!?！？）、empty/whitespace
- **_group_words_to_paragraphs**：合成 word dict、同/异行合并、bbox 聚合
- **_lines_to_para**：empty → text=""、bbox=None；按 x0 排序；bbox=[min(x0),min(top),max(x1),max(bottom)]
- **FallbackParser 类**：name="fallback"、version 含 pdfplumber/python-docx/pypdfium2、init 签名 (self, image_output_dir=None)、str 转 Path、None 保留
- **parse 错误**：file_not_found/unsupported_type，details.path 精确
- **模块结构**：__all__=["FallbackParser"]、try/except optional imports、_PDFPLUMBER_VERSION/_DOCX_VERSION/_PDFIUM_VERSION 常量、docstring 提及 pdfplumber/python-docx/Kreuzberg 限制

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 167 后）：13486 pass / 0 fail / 13 skip（HEAD `a487985`）

### 下一步建议
- 候选 IC：app/parsers/text_parser.py 第七轮
- 候选 IE：app/parsers/kreuzberg_parser.py 第六轮
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/models.py 第八轮
- 候选 IJ：app/chunkers/base.py 第六轮（若有）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IC（app/parsers/text_parser.py 第七轮）。text_parser 是最简单的 parser，
第七轮可深入 line/word 切分、空行处理、metadata 字段等。

---

## Round 168（2026-08-05）：app/parsers/text_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/text_parser.py（136 行，已有 base/edges/edges2-5 共 455 测试）补第六轮
- 深入 _split_paragraphs 换行归一与 _detect_text_source_type details

### 改动
- 新增 `tests/test_parsers_text_edges6.py`（88 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_TEXT_EXTENSIONS**：精确 (".txt", ".text")
- **_detect_text_source_type**：大小写、details.suffix 精确、message 提及 .txt/.text
- **_split_paragraphs**：
  - empty → []
  - 单 paragraph / 多 paragraph 分隔
  - 连续空行视为单一分隔
  - leading/trailing blank 行 skip
  - CRLF/CR 归一为 LF
  - whitespace-only 行视为空行
  - 仅空白 → []
  - 连续非空行合并（保留内部 \n）
  - 1-based 行号
  - content strip 外部空白、保留内部 \n
  - idempotent、no mutation
- **TextParser 类**：name="text"、version="stdlib/0.1.0"、继承 Parser
- **parse 错误**：file_not_found、unsupported_type
- **parse metadata**：{"text": True}、source_type="text"
- **场景**：empty/whitespace-only 触发 text_no_content；CRLF/Unicode/invalid UTF-8（errors=replace）
- **element_id**：zero-pad 4 位、连续递增
- **locator**：1-based line
- **confidence**：0.95 默认、metadata={}
- **模块结构**：__all__、future annotations、imports、docstring 提及策略与不支持功能
- **签名深度**：parse/_detect/_split_paragraphs

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 168 后）：13574 pass / 0 fail / 13 skip（HEAD `21fa8ea`）

### 下一步建议
- 候选 IE：app/parsers/kreuzberg_parser.py 第六轮
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/models.py 第八轮
- 候选 IK：app/hash.py 第六轮（计算 source_hash 的入口）
- 候选 IL：app/source_locator.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IE（app/parsers/kreuzberg_parser.py 第六轮）。kreuzberg 是可选 parser 路径，
第六轮可深入 KreuzbergParser 类、可选 import fallback、版本字符串等。

---

## Round 169（2026-08-05）：app/parsers/kreuzberg_parser.py 第六轮（edges6）

### 目标
- 给 app/parsers/kreuzberg_parser.py（245 行，已有 base/edges/edges2-5 共 717 测试）补第六轮
- 深入 _classify_line 启发式、_make_locator 分支、_split_content_to_elements 纯函数

### 改动
- 新增 `tests/test_parsers_kreuzberg_edges6.py`（86 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量**：_HEADING_RE 是 re.Pattern、匹配 markdown 风格 # heading（1-6 级，7 级不匹配）、_SHORT_LINE_MAX=80
- **_classify_line**：
  - atx # / ## / ###### heading，level 与 raw_text
  - short_line（≤80 且无结尾标点）→ heading level=0 heuristic=short_line
  - 81 chars → paragraph
  - 结尾标点 . 。 ? ? ! ! → paragraph
  - empty/whitespace → paragraph meta={}
  - atx 优先于 short_line
  - atx 前可有空白
- **_make_locator**：
  - pdf → {page:1, _kreuzberg_placeholder:True}（忽略 paragraph_index）
  - docx → {paragraph_index:N, _kreuzberg_heuristic:True}（忽略 page）
- **_split_content_to_elements**：
  - empty → []
  - 单/多 paragraph 切分（双换行）
  - heading confidence=0.6、paragraph confidence=0.5
  - paragraph metadata 含 kreuzberg_heuristic=True
  - element_id zero-pad 4 位、连续
  - locator 跟随 source_type（pdf vs docx）
  - 多空白行视为单一分隔
  - heading 后接正文（同 block）→ 1 heading + 1 paragraph
- **KreuzbergParser 类**：name="kreuzberg"、version 字符串、__init__ keyword-only include_document_structure=True、继承 Parser
- **parse() 错误**：file_not_found（先校验文件）、unsupported_type
- **模块结构**：__all__、optional import try/except、_KREUZBERG_AVAILABLE/_VERSION 常量、docstring 提及 4.10.2 与"业务代码"
- **签名深度**：所有公共/内部函数

### 撞墙记录
- **Wall 1**：测试用 "hello" 期望 paragraph，实际 _classify_line 把短文本判为 heading（short_line heuristic）。
  修复：单 paragraph 测试改用 >80 字符或带句号的长文本。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 169 后）：13660 pass / 0 fail / 13 skip（HEAD `aa4bd3d`）

### 下一步建议
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/models.py 第八轮
- 候选 IK：app/hash.py 第六轮
- 候选 IL：app/source_locator.py 第六轮
- 候选 IM：app/pipeline.py 第六轮（核心 pipeline）
- 候选 IN：app/schema.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IM（app/pipeline.py 第六轮）。pipeline 是整个流程的串联入口，
第六轮可深入 parse→chunk→validate 各阶段、错误聚合、structured errors JSON 输出。

---

## Round 170（2026-08-05）：app/pipeline.py 第七轮（edges7）

### 目标
- 给 app/pipeline.py（216 行，已有 edges/edges2-6/errors/helpers/integration 共 639 测试）补第七轮
- 深入 get_parser 各分支、image_output_dir_for、process_single 错误路径、validate_only

### 改动
- 新增 `tests/test_pipeline_edges7.py`（63 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_parser**：6 parser 全覆盖、未知 name 抛 ValueError（消息列出所有支持项）、fallback 接受 image_output_dir、其他 parser 忽略、返回 Parser 子类、每次新实例
- **image_output_dir_for**：None→None、Path/str 都接受、命名约定 `images-<sha16>`、parent 与 output_path.parent 一致、短 hash 仍按 [:16] 取
- **process_single**：
  - 错误路径：file_not_found（details.path）、unknown_parser（兜底 unexpected）、unsupported_type、empty file → no_extracted_elements（details 含 warnings/source_type）
  - 成功路径：text parser、不写盘也返回 Document、写盘创建 parent dir、write_json=False 不写
  - keyword-only 参数（parser_name/max_chars/write_json）
  - 默认值精确（fallback/800/True）
- **validate_only**：不存在/非法 JSON/返回 (bool, str)
- **模块结构**：__all__ 4 项、imports 完整（json/Path/Any/StructuralChunker/compute_file_hash/所有 6 parser/SchemaValidationError/validate）、docstring 提及关键不变量
- **签名深度**：所有公共函数参数名、默认值、keyword-only kind
- **综合行为**：idempotent、no mutation、长 paragraph 自动分块、不同 parser name 返回不同类实例

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 170 后）：13723 pass / 0 fail / 13 skip（HEAD `3f222b5`）

### 下一步建议
- 候选 IG：app/chunkers/__init__.py 第六轮
- 候选 IH：app/models.py 第八轮
- 候选 IK：app/hash.py 第六轮
- 候选 IL：app/source_locator.py 第六轮
- 候选 IN：app/schema.py 第六轮
- 候选 IO：app/cli.py 第八轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IG（app/chunkers/__init__.py 第六轮）。chunkers/__init__.py 是分块器子包入口，
第六轮可深入 StructuralChunker re-export、__all__、与其他 chunker 子模块的关系。

---

## Round 171（2026-08-05）：app/chunkers/__init__.py 第六轮（init_edges）

### 目标
- 给 app/chunkers/__init__.py（7 行，仅 re-export）补强
- 深入 __all__、重导出 identity、子模块可导入

### 改动
- 新增 `tests/test_chunkers_init_edges.py`（29 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **__all__ 精确**：2 项 `["StructuralChunker", "normalize_text"]`、list、无重复
- **重导出 identity**：pkg.X is structural.X
- **公共 API 类型**：StructuralChunker 是 class、normalize_text 可调用
- **子模块可导入**：app.chunkers.structural
- **模块结构**：docstring、__future__ annotations、from .structural import、__file__ 以 __init__.py 结尾
- **子包目录**：__init__.py + structural.py
- **star import**：只导入 __all__ 中的 2 个名字
- **normalize_text 行为**：idempotent、empty/no-whitespace

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 171 后）：13752 pass / 0 fail / 13 skip（HEAD `cdf3008`）

### 下一步建议
- 候选 IH：app/models.py 第八轮
- 候选 IK：app/hash.py 第六轮
- 候选 IL：app/source_locator.py 第六轮
- 候选 IN：app/schema.py 第六轮
- 候选 IO：app/cli.py 第八轮
- 候选 IP：app/chunkers/structural.py 第八轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IH（app/models.py 第八轮）。models 是数据模型核心，
第八轮可深入各 dataclass field 默认值、FrozenInstanceError、asdict、to_dict 等。

---

## Round 172（2026-08-05）：app/models.py 第六轮（edges6）

### 目标
- 给 app/models.py（154 行，已有 base/edges/edges2-5 共 474 测试）补第六轮
- 深入各 dataclass 字段精确值、__post_init__ 校验、to_dict 行为

### 改动
- 新增 `tests/test_models_edges6.py`（80 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMA_VERSION**：精确 "0.1.0"、X.Y.Z 格式
- **ElementType Literal**：精确 8 个值（heading/paragraph/list_item/table/image/caption/header/footer）
- **SourceType Literal**：精确 6 个值（pdf/docx/markdown/html/text/ipynb）
- **Element dataclass**：8 字段精确名、必填 3 个（element_id/type/source_locator）、可选 5 个、metadata default_factory
- **Element __post_init__**：empty id、no content+resource、empty content + None resource、only resource、both
- **Element.to_dict**：返回 dict、含 8 字段、值保留、== asdict
- **Chunk dataclass**：5 字段、3 必填、metadata/source_spans default_factory、3 个 __post_init__ 校验
- **Relation dataclass**：4 字段、3 必填、metadata default_factory、to_dict == asdict
- **WarningRecord dataclass**：3 字段、code/reason 必填、details default None、to_dict 自定义（None details 不含键）
- **ErrorRecord dataclass**：同 WarningRecord
- **Document dataclass**：12 字段、6 必填、6 collection default_factory、to_dict 含 schema_version、递归序列化嵌套
- **模块结构**：无 __all__、future annotations、imports 完整（dataclass/field/asdict/Any/Literal/Optional）、docstring 提及业务代码隔离
- **综合行为**：Element/Chunk/Relation 的 to_dict == asdict；WarningRecord/ErrorRecord 的 to_dict ≠ asdict（自定义）、metadata 每实例独立

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 172 后）：13832 pass / 0 fail / 13 skip（HEAD `5824857`）

### 下一步建议
- 候选 IK：app/hash.py 第六轮
- 候选 IL：app/source_locator.py 第六轮
- 候选 IN：app/schema.py 第六轮
- 候选 IO：app/cli.py 第八轮
- 候选 IP：app/chunkers/structural.py 第八轮
- 候选 IQ：app/__init__.py 第六轮（app package 入口）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IN（app/schema.py 第六轮）。schema.py 是 JSON Schema 校验入口，
第六轮可深入 validate/validate_file/SchemaValidationError/各 schema 文件加载。

---

## Round 173（2026-08-05）：app/schema.py 第六轮（edges6）

### 目标
- 给 app/schema.py（93 行，已有 base/edges/edges2-5 共 618 测试）补第六轮
- 深入 SchemaValidationError、load_schema、validate 各分支

### 改动
- 新增 `tests/test_schema_edges6.py`（80 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMA_PATH**：精确路径（project_root/schemas/document.schema.json）、绝对、resolve 无 ..、文件名/父目录、is_file
- **SchemaValidationError**：init 签名（message, errors）、errors 默认 None→[]、显式 None/[]/[err]、str==message、args==(message,)、继承 Exception 不继承 ValueError、可被 except 捕获
- **load_schema**：默认返回 dict、== load_schema(SCHEMA_PATH)、str path、不存在/目录/无效 JSON 抛错、每次返回新 dict、签名仅 path
- **validate**：空 schema→无错误返回 None、不传 schema 用默认、收集所有错误、path 空/含字段、message 是 str、schema_path 是 list、异常消息含"Schema/校验失败/处"、不修改 document、签名 (document, schema)
- **is_valid**：true/false/bool 类型、不抛异常、默认 schema、签名、返回 bool
- **validate_file**：缺失/无效 JSON/str path/目录 各错误路径、签名
- **默认 schema**：Draft202012Validator.check_schema 通过、$schema/type/properties top keys、type==object、properties 含 document_id/chunks
- **模块结构**：__all__ 精确 6 项无重复、future annotations、imports json/Path/Any/Draft202012Validator/JSValidationError、docstring 提及业务代码、_silence_unused_import 函数
- **综合行为**：validate↔is_valid 一致、load_schema 幂等、validate 幂等、load_schema 默认从 SCHEMA_PATH、validate 不修改 schema

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 173 后）：13912 pass / 0 fail / 13 skip（HEAD `9e29465`）

### 下一步建议
- 候选 IK：app/hash.py 第六轮（158 行，478 测试）
- 候选 IL：app/source_locator.py 第六轮
- 候选 IO：app/cli.py 第八轮
- 候选 IP：app/chunkers/structural.py 第八轮
- 候选 IQ：app/__init__.py 第六轮（app package 入口）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IK（app/hash.py 第六轮）。hash.py 是文件哈希入口，
第六轮可深入 compute_file_hash 各 chunk size、make_document_id 各边界、SHA-256 一致性。

---

## Round 174（2026-08-05）：evaluation/cli.py 第七轮（edges7）

### 目标
- 给 evaluation/cli.py（243 行，已有 base/edges/edges2-6 共 571 测试）补第七轮
- 深入 _build_parser 参数精确集合、_format_metric 各类型分支、main() 各退出码

### 改动
- 新增 `tests/test_evaluation_cli_edges7.py`（93 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser**：3 个 subparser 各自参数精确集合（去除 command/help）、run subparser 5 args（manifest/output required、parser choices fallback+kreuzberg、max_chars/tolerance_chars type=int default）、validate-report 1 arg（input）、inspect-doc 2 args（input、tolerance_chars）、subparsers required=True、prog/description/formatter_class
- **_format_metric**：None/bool/float/int/str/list/dict 各分支、float .4f 精度、dict 按 key 排序、name padding 36、long name 不截断、bool/float reason 保留（or 'ok'）
- **_run_inspect_doc**：nonexistent→2、invalid JSON→1、list top→1、empty dict→0、Path 对象接受、str 接受
- **main()**：no args→SystemExit(2)、unknown command→SystemExit、invalid parser choice→SystemExit(2)、missing required arg→SystemExit、run nonexistent manifest→2、validate-report nonexistent→2、validate-report invalid JSON→1、validate-report schema-invalid→1、validate-report FileNotFoundError→2、inspect-doc 各错误码
- **模块结构**：无 __all__、future annotations、imports（argparse/json/sys/Path + manifest/report/runner/schema 各 import）、stdout reconfigure 块在 try/except (AttributeError, OSError)、docstring 含 run/validate-report/inspect-doc + sanity
- **签名**：main(argv: list[str] | None = None) -> int、_build_parser() -> ArgumentParser、_format_metric(name: str, metric: dict) -> str、_run_inspect_doc(args) -> int
- **综合行为**：build_parser 幂等返回新实例、format_metric 不修改输入、run→validate-report roundtrip、inspect-doc 真实 doc 端到端、--tolerance-chars 透传

### 撞墙记录
- 一次撞墙（5 fail）：
  - subparser 参数集合含 'command'（来自 subparsers 父 action）→ 改为排除 command
  - bool + reason 测试期望 'ok' 覆盖 reason，实际 reason truthy 时保留 → 改为 reason 保留

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 174 后）：14005 pass / 0 fail / 13 skip（HEAD `5acf34c`）

### 下一步建议
- 候选 IK：app/hash.py 第六轮（24 行 / 266 测试，已饱和）
- 候选 IR：evaluation/runner.py 第七轮（227 行 / 569 测试）
- 候选 IS：evaluation/metrics.py 第七轮（381 行 / 951 测试）
- 候选 IT：evaluation/manifest.py 第七轮（239 行 / 731 测试）
- 候选 IU：evaluation/report.py 第六轮（200 行 / 576 测试）
- 候选 IV：evaluation/schema_validation.py 第二轮（15 行 / 112 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IR（evaluation/runner.py 第七轮）。runner.py 是评测主流程入口，
第七轮可深入 _load_annotation 各异常分支、_process_one image_dir 命名、run_evaluation expected_failures 流程。

---

## Round 175（2026-08-05）：evaluation/runner.py 第七轮（edges7）

### 目标
- 给 evaluation/runner.py（227 行，已有 base/edges/edges2-6 共 569 测试）补第七轮
- 深入 _load_annotation 异常分支、_process_one 错误码与 image_dir、run_evaluation expected_failures 流程

### 改动
- 新增 `tests/test_evaluation_runner_edges7.py`（66 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation**：None/不存在/目录/JSONDecodeError 各分支精确、返回新 dict 每次调用、签名 (path: Path | None) -> dict | None
- **_process_one**：返回 5 元组、success 路径（document_dict/parser_version/total_seconds/image_dir 类型）、failure 路径（document None + error_dict 非 None + image_dir None）、_per_doc 目录创建、out_stub 成功后清理、签名（4 参数无默认值）
- **run_evaluation expected_failures**：matches=True/mismatch/no_actual_error/empty 各分支
- **run_evaluation per_doc 私有字段分离**：公开 per_doc 不含 _annotation_present/_tolerance_chars/_missing_markers、keys 精确 4 项
- **run_evaluation wall_time_seconds**：5 keys（total/parse/chunk/parse_reason/chunk_reason）、parse/chunk null、reason not_instrumented
- **run_evaluation 报告结构**：6 顶层 keys、empty manifest 处理、output_path.parent 自动创建、JSON 写盘
- **run_evaluation keyword-only**：parser_name/max_chars/tolerance_chars 都是 KEYWORD_ONLY
- **模块结构**：__all__ 精确 ["run_evaluation"]、future annotations、imports（json/time/Path/Any + pipeline/evaluation/annotation_metrics/metrics/report）、docstring 提及 perf_counter/not_instrumented
- **综合行为**：幂等（同输入两次跑结果一致）、kreuzberg parser 不抛、_per_doc 目录无残留 stub

### 撞墙记录
- 一次撞墙（2 fail）：
  - _process_one 的 parser_name/max_chars 实际是必填（无默认值）→ 改为 no_default 测试

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 175 后）：14071 pass / 0 fail / 13 skip（HEAD `2c3e4f6`）

### 下一步建议
- 候选 IS：evaluation/metrics.py 第七轮（381 行 / 951 测试）
- 候选 IT：evaluation/manifest.py 第七轮（239 行 / 731 测试）
- 候选 IU：evaluation/report.py 第六轮（200 行 / 576 测试）
- 候选 IV：evaluation/schema_validation.py 第二轮（15 行 / 112 测试，已饱和）
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IU（evaluation/report.py 第六轮）。report.py 是评测报告装配核心，
第六轮可深入 aggregate_summary 各 metric 类型、build_provenance git 字段、build_devset_section 各 key 精确。

---

## Round 176（2026-08-05）：evaluation/report.py 第六轮（edges6）

### 目标
- 给 evaluation/report.py（200 行，已有 base/edges/edges2-5 共 576 测试）补第六轮
- 深入 get_git_provenance subprocess 参数、get_dependency_versions 包名顺序、aggregate_summary figure_caption 排除

### 改动
- 新增 `tests/test_evaluation_report_edges6.py`（93 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_git_provenance subprocess 参数**：用 patch.object 检查 cwd=str(project_root)、capture_output=True、text=True、encoding=utf-8、errors=replace、timeout=10
- **get_git_provenance 各 returncode/stdout 分支**：empty stdout→commit None、strip 空白、porcelain returncode!=0 → dirty=False（非 True！）
- **get_git_provenance 异常路径**：OSError/SubprocessError/TimeoutExpired 都被 (OSError, SubprocessError) 捕获
- **get_dependency_versions**：包名顺序固定（pdfplumber→python-docx→pypdfium2）、PackageNotFoundError→None、generic Exception→None、只查 3 个包
- **build_provenance**：9 keys 精确集合、git_commit str|None、git_dirty bool、dependencies dict、max_chars int（接受 float/numeric str）、run_timestamp_iso 含 T 分隔符
- **aggregate_summary**：figure_caption_precision/recall/f1 显式不在 ratio_macro_averages、未知 metric 忽略、metric 无 value 跳过、negative value 参与、explicit zero 参与
- **aggregate_summary success_rates**：value=False 不计 success、value=None 不计但 total+1
- **aggregate_summary keys 精确**：counts/success_rates/ratio_macro_averages/silent_drop_total 4 项
- **build_devset_section**：categories_covered 引用语义（不去重、保序）
- **模块注释**：figure_caption 始终 null 不参与 macro average（源码注释明确）、__all__ 5 项
- **综合行为**：每次新 dict、不修改输入、100 docs 聚合正确

### 撞墙记录
- 一次撞墙（1 fail）：
  - 测试期望 porcelain returncode!=0 → dirty=True（默认值），实际 bool(returncode==0 and ...)=False → 改为 dirty=False

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 176 后）：14164 pass / 0 fail / 13 skip（HEAD `7fb9a69`）

### 下一步建议
- 候选 IS：evaluation/metrics.py 第七轮（381 行 / 951 测试）
- 候选 IT：evaluation/manifest.py 第七轮（239 行 / 731 测试）
- 候选 IV：evaluation/schema_validation.py 第二轮（15 行 / 112 测试，已饱和）
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IS（evaluation/metrics.py 第七轮）。metrics.py 是评测指标计算核心，
第七轮可深入 compute_automatic_metrics 各 metric 边界（None/0/negative/missing 字段）。

---

## Round 177（2026-08-05）：evaluation/metrics.py 第七轮（edges7）

### 目标
- 给 evaluation/metrics.py（381 行，已有 base/edges/edges2-6 共 951 测试）补第七轮
- 深入 _image_resource_ratio 各 OSError/size 0/relative path 分支、_text_preservation multiset 语义、_chunk_reference_ratio 各分支

### 改动
- 新增 `tests/test_evaluation_metrics_edges7.py`（76 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_image_resource_ratio**：resource_path 缺失/空/不存在/size 0 各跳过、mixed valid、relative + image_base_dir 拼 .name、image_base_dir=None 时只用原始 Path
- **_text_preservation**：empty expected/actual 各 precision/recall null 路径、重复字符 min 交集、reorder 改 equal 不改 multiset、image content 不参与 expected、全空白 expected → empty_expected reason
- **_text_preservation 公式**：precision=common/|actual|、recall=common/|expected|、extra chars in actual → precision<1.0 recall=1.0
- **_chunk_reference_ratio**：empty chunks → no_chunks、empty elements with chunks → 0.0、source_element_ids=None falsy 跳过、all valid/partial 各 ratio
- **_silent_drop_count**：negative/zero expected no drop、unexpected type 0 actual、actual > expected → 0
- **compute_automatic_metrics**：error_code 内联 dict 结构、source_type 非 pdf/docx 各 null reason、pipeline_failed 11 metric keys 全 null + pipeline_failed reason、成功路径 14 keys、element_count_by_type 含 image
- **模块结构**：__all__ 精确、imports（math/Counter/Path/Any）、docstring 提及 Counter/纯函数/不伪造、helper functions 14 个都存在
- **综合行为**：每个 helper 幂等、不修改输入、_null/_ratio 互不影响

### 撞墙记录
- 一次撞墙（1 fail）：
  - _image_resource_ratio 本身 image_base_dir 无默认值（必填）→ 改为 no_default 测试

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 177 后）：14240 pass / 0 fail / 13 skip（HEAD `ca4a8a9`）

### 下一步建议
- 候选 IT：evaluation/manifest.py 第七轮（239 行 / 731 测试）
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 候选 IZ：evaluation/annotation_metrics.py 第七轮（194 行 / 523 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IT（evaluation/manifest.py 第七轮）。manifest.py 是清单加载核心，
第七轮可深入 DocumentEntry/ExpectedFailure frozen dataclass 边界、_resolve_relative_path 错误消息、content_group_count 链式配对。

---

## Round 178（2026-08-05）：evaluation/manifest.py 第七轮（edges7）

### 目标
- 给 evaluation/manifest.py（239 行，已有 base/edges/edges2-6 共 731 测试）补第七轮
- 深入 _detect_project_root、content_group_count frozenset 去重、load_manifest optional fields 默认值

### 改动
- 新增 `tests/test_evaluation_manifest_edges7.py`（90 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_detect_project_root**：dir/file/ancestor 查找 pyproject.toml、无 pyproject 时回退 cur、返回 Path 类型、resolve()
- **content_group_count**：self-pairing frozenset([d,d])={d}、bidirectional pair 去重、three-way cycle 3 groups、all_paired、mixed、empty docs、single with missing partner（frozenset 仍包含）各边界
- **categories_covered**：empty docs → []、单 doc 多 categories、跨 doc set union 去重、字母排序、返回 list、无重复
- **load_manifest**：schema 校验先于 version mismatch、optional fields 缺失默认（categories → ()、paired_with/sha256/source_type/annotation_file/expectations → None）、annotation_file 解析为 resolved 路径、Manifest 实例化各字段
- **_resolve_relative_path**：field_name 嵌入错误消息、empty/absolute_posix/absolute_windows/backslash/outside_root 各 reason 文本精确
- **DocumentEntry/ExpectedFailure/Manifest frozen**：FrozenInstanceError、is_dataclass、字段数（10/5/5）
- **Manifest properties**：file_count/pdf_count/docx_count 计数正确
- **ManifestError**：inherits Exception、not ValueError、可被捕获
- **模块结构**：__all__ 精确 5 项、imports 完整（json/dataclass/Path/Any/MANIFEST_VERSION/validate）、docstring 提及 3 大不变量
- **签名**：load_manifest(manifest_path, project_root=None)、_resolve_relative_path(path_str, project_root, field_name)
- **综合行为**：幂等、显式 project_root 跳过 detect、str path 接受、properties 不修改 documents

### 撞墙记录
- 一次撞墙（2 fail）：
  - manifest_version="0.0.0" 在 schema 层就被拒（schema 要求 enum["1.0"]）→ 改为期待 EvalSchemaError
  - DocumentEntry 实际 10 个字段（含 annotation_file_str + annotation_resolved），非 9 → 改为 10

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 178 后）：14330 pass / 0 fail / 13 skip（HEAD `53ece42`）

### 下一步建议
- 候选 IZ：evaluation/annotation_metrics.py 第七轮（194 行 / 523 测试）
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 候选 JA：evaluation/schema.py 第二轮（80 行 / 432 测试）
- 候选 JB：evaluation/schema_validation.py 第二轮（15 行 / 112 测试，已饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IZ（evaluation/annotation_metrics.py 第七轮）。annotation_metrics.py 是
人工标注指标核心，第七轮可深入 chunk_boundary_prf 容差匹配、figure_caption_prf 各 null reason、_missing_markers 计算。

---

## Round 179（2026-08-05）：evaluation/annotation_metrics.py 第七轮（edges7）

### 目标
- 给 evaluation/annotation_metrics.py（194 行，已有 base/edges/edges2-6 共 523 测试）补第七轮
- 深入 chunk_boundary_prf 一对一匹配语义、anchor position 分支、missing marker 处理、f1 各分支

### 改动
- 新增 `tests/test_annotation_metrics_edges7.py`（56 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **chunk_boundary_prf 一对一匹配**：多预测 1 anchor 只 1 match、1 预测多 anchor 只 1 match、贪心 by distance 排序、used_pred/used_gt 不能 rematch
- **anchor position 各分支**：before=marker 起始、after=marker 结束、缺省 position 走 after、未知 position 也走 after
- **missing marker 处理**：marker 在 stream 找不到 → 加入 _missing_markers value 列表、空 marker 也算 missing、1 个 missing 不影响其他 anchor、all missing → recall null "no_ground_truth_anchors_in_stream"
- **chunk text 边界**：empty chunk text 不抛异常
- **f1 各分支**：perfect=1.0、half-half=2/3、p null（单 chunk 早期返回）→ reason "no_predicted_boundaries"、r null（marker all missing）→ reason "precision_or_recall_not_evaluated"、denom=0 → _ratio(0.0)
- **tolerance 透传**：=0 only exact match、off-by-one 不匹配、_tolerance_chars 始终在 result 中
- **figure_caption_prf**：3 metric reason 都是 PARSER_DOES_NOT_EMIT_RELATIONS、3 keys 精确、orphan relations field 仍 null、无 _tolerance_chars
- **模块结构**：__all__ 精确 3 项、imports normalize_text/_null/_ratio、docstring 提及启发式/一对一/容差
- **综合行为**：幂等、每次新 dict、不修改 document/annotation、JSON 可序列化

### 撞墙记录
- 一次撞墙（2 fail）：
  - "alpha" 后置 + "lph" 后置：search_from 推进后 "lph" 找不到（只 1 个 gt position）→ recall=1.0，原期望 0.5 错
  - 单 chunk + anchor 走早期返回路径 → f1 reason 是 "no_predicted_boundaries"（不是 "precision_or_recall_not_evaluated"）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 179 后）：14386 pass / 0 fail / 13 skip（HEAD `4266d61`）

### 下一步建议
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 候选 JA：evaluation/schema.py 第二轮（80 行 / 432 测试）
- 候选 JB：evaluation/schema_validation.py 第二轮（15 行 / 112 测试，已饱和）
- 候选 JC：app/parsers/* 各第 N 轮（多个 parser 仍有 6-7 轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 JA（evaluation/schema.py 第二轮）。schema.py 是评测 Schema 校验入口，
第二轮可深入 validate/validate_file 各错误路径、EvalSchemaError 字段、各 schema 文件加载。

---

## Round 180（2026-08-05）：evaluation/schema.py 第五轮（edges5）

### 目标
- 给 evaluation/schema.py（80 行，已有 base/edges/edges2/edges3/edges4 共 472 测试）补第五轮
- 深入 SCHEMAS_DIR 路径精确、EvalSchemaError 继承层级、validate_file 错误优先级

### 改动
- 新增 `tests/test_evaluation_schema_edges5.py`（86 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMAS_DIR**：路径精确（project_root/schemas）、绝对、resolve 无 ..、is_dir、父目录含 pyproject.toml、3 个 known schema 文件存在
- **EvalSchemaError**：init 签名 (message, errors=None)、errors 默认 None→[]、透传 errs、super().__init__(message) → args==(message,)、继承 Exception 不继承 ValueError/KeyError、FileNotFoundError 不能捕获
- **_schema_path**：错误消息含路径、目录也 raise FileNotFoundError、返回绝对 Path
- **load_schema**：3 个 known schema（manifest/annotation/evaluation-report）都可加载、Draft202012 兼容、含 $schema/properties、每次新 dict
- **validate**：错误聚合 path/message/schema_path 各类型、消息含 schema_name+count、不修改 instance
- **validate_file 错误优先级**：FileNotFoundError > JSONDecodeError > EvalSchemaError（用 priority 测试验证）
- **模块结构**：__all__ 精确 5 项、imports 完整（json/Path/Any/Draft202012Validator/JSValidationError）、docstring 提及不与 app/schema.py 复用
- **签名**：validate(instance, schema_name)、validate_file(path, schema_name) 都无默认值
- **综合行为**：幂等、validate/validate_file 一致、EvalSchemaError 多错误保留

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 180 后）：14472 pass / 0 fail / 13 skip（HEAD `1614d03`）

### 下一步建议
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IX：app/pipeline.py 第八轮（216 行 / 702 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 候选 J D：app/parsers/* 各第 N 轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IX（app/pipeline.py 第八轮）。pipeline.py 是处理流程核心，
第八轮可深入 process_single 各 parser 路径、validate_only 错误聚合、image_output_dir_for 边界。

---


## Round 181（2026-08-05）：app/pipeline.py 第八轮（edges8）

### 目标
- 给 app/pipeline.py（216 行，已有 edges/edges2-7/errors/helpers/integration 共 702 测试）补第八轮
- 深入 get_parser 各路径、process_single 各错误码、validate_only 各错误消息

### 改动
- 新增 `tests/test_pipeline_edges8.py`（86 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_parser**：大小写敏感（大写/小数/空字符串/前后空格/部分名都 raise ValueError）、各 parser 名返回正确 Parser 子类、image_output_dir str/Path 都接受
- **image_output_dir_for**：source_hash 长度边界（16/17/15/1/empty/64）、含父目录路径、根路径、Windows 风格反斜杠
- **process_single 错误码**：file_not_found / unsupported_type / no_extracted_elements / unexpected_parser_error 各路径
- **process_single 各 parser 成功**：text/markdown/html/ipynb 都返回 document + 写盘
- **process_single 写盘行为**：indent=2、UTF-8 ensure_ascii=False、mkdir parents=True、write_json=False 跳过写盘
- **process_single 签名**：keyword-only args、各默认值
- **validate_only**：合法 doc → (True, 'OK')、各错误消息（missing/json/schema）、str path 也接受
- **模块结构**：__all__ 精确 4 项、imports 完整、docstring 完整
- **综合**：幂等、process_single + validate_only roundtrip、kreuzberg parser 名

### 撞墙记录
- 初版 2 处 fail：合法 doc 用 source_type=text + 空 source_locator，schema 要求 source_locator.line。
  改用 source_type=docx + paragraph_index=0 + 完整 element 字段（parent_id/confidence/metadata）+ chunk metadata，对齐现有 helpers 测试的 valid_doc 结构。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 181 后）：14558 pass / 0 fail / 13 skip（HEAD `8ae5b8b`）

### 下一步建议
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 IY：app/chunkers/structural.py 第八轮（388 行 / 938 测试）
- 候选 JD：app/parsers/* 各第 N 轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IY（app/chunkers/structural.py 第八轮）。structural 是分块核心，
第八轮可深入 heading 级别判定、source_element_ids 聚合、normalize_text 边界、空 chunk 处理。

---


## Round 182（2026-08-05）：app/chunkers/structural.py 第八轮（edges8）

### 目标
- 给 app/chunkers/structural.py（388 行，已有 base/edges/edges2-7 共 939 测试）补第八轮
- 深入 regex 实际拆分行为、_hard_split 边界、_split_long_text 累积、_ChunkBuffer 多 part 行为

### 改动
- 新增 `tests/test_chunker_edges8.py`（134 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_SENTENCE_SPLIT_RE 实际拆分**：需标点 + 空白才切（中文句号无空白不切）、各标点（中英文）、无标点不切、空串
- **_WHITESPACE_RE 实际替换**：单空格/多空格/tab/newline/CRLF/mixed/无空白
- **_hard_split_with_whitespace_fallback**：whitespace 在 upper/lower 边界、连续空白跳过、max_chars=32 最小、自然结尾 boundary_after=None、whitespace 切开后还有非空白时 boundary_after='whitespace'
- **_split_long_text 累积与坐标**：累积超限 flush、mixed 长短句、坐标在 stripped text 系、forced_char 边界、保留 normalize 等价
- **_ChunkBuffer 深度**：length 含 unicode、push_text 多 part、flush dedup 顺序与 span 数量、whitespace-only part 被 strip 后返回 None、dataclass 字段
- **_SplitPiece 深度**：默认值、frozen setattr raises、equality、repr
- **模块常量精确值**：_PART_TEXT=0/_PART_ELEMENT_ID=1/_PART_START=2/_PART_END=3、_HARD_BREAK_LANGS 含 6 个标点
- **StructuralChunker.chunk 行为**：heading/table/image/caption/list_item/unknown 各路径、long_paragraph split、chunk_id 格式与递增、metadata strategy、不丢不重 normalize 验证
- **_element_text_with_span 深度**：内部空白保留、tab/newline 边界、unicode 内容、image 返回空
- **normalize_text 深度**：idempotent、unicode、falsy 输入
- **模块结构**：__all__ 精确 2 项、imports 完整、docstring 提及 heading boundary/不修改/source_spans

### 撞墙记录
- 初版 3 处 fail：
  1. _SENTENCE_SPLIT_RE 需 (?<=punct)\s+ 才切，中文句号无空白不切 → 改测试加空白
  2. leading whitespace 无前置标点时不切 → 改测试期望
  3. forced_char 硬切不补空白，破坏 normalize 等价 → 改测试用有空白的文本

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 182 后）：14692 pass / 0 fail / 13 skip（HEAD `09322ec`）

### 下一步建议
- 候选 IW：app/cli.py 第八轮（535 行 / 747 测试）
- 候选 JE：app/parsers/text.py 第七轮（如还有 gap）
- 候选 JF：app/parsers/fallback.py 第七轮（如还有 gap）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 IW（app/cli.py 第八轮）。cli.py 是命令行入口，第八轮可深入各子命令错误路径、argparse 行为、退出码细节。

---


## Round 183（2026-08-05）：app/cli.py 第七轮（edges7）

### 目标
- 给 app/cli.py（535 行，已有 base/edges/edges2-6 共 747 测试）补第七轮
- 深入 _preview 边界、_load_document_json 错误路径、_format_* 显示规则、main() 错误码

### 改动
- 新增 `tests/test_cli_edges7.py`（153 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_preview 深度**：None/empty/whitespace 输入、空白归一（多空格/newline/tab/mixed）、CJK 文本宽度按 1 计、width=0/1 边界、width 巨大不切
- **_load_document_json 深度**：BOM 在 utf-8 下失败、empty 文件、顶层 list/string 合法、返回 tuple 结构
- **_format_summary 深度**：缺各 key 用 ? 占位、warnings/errors 超 5 截断、elements 按 type 计数、hash 前 16+…、无 warnings/errors 不显示该段
- **_format_elements_list 深度**：limit<=0 全列、limit 超过显示 +N more、parent_id 显示规则、preview 长内容截断
- **_format_chunks_list 深度**：show_spans=True 且 spans=[] 显示 (none)、spans 缺 key 也显示 (none)、text=None 当 0 处理
- **_iter_supported_files 深度**：目录即使带支持后缀也过滤、unsupported 后缀过滤、recursive 包含子目录、大写/混合大小写后缀
- **_relative_output_path 深度**：嵌套子目录、suffix 保留到文件名、Windows 反斜杠 normalize
- **_build_arg_parser 深度**：各子命令必填参数缺失 exit 2、各 default 值、unknown command/parser exit 2
- **_emit_structured_error 深度**：复杂 nested dict extra、code/message 总在、input 序列化为 str、indent=2、无 extra 时只有 code/message
- **_infer_parser_name 全 9 后缀**：各后缀 → 各 parser、未知 → fallback、无后缀 → fallback、大写/混合大小写
- **main() 错误路径**：validate missing file exit 2、inspect missing file exit 2、inspect invalid json exit 1、inspect top-level list exit 1、valid doc inspect exit 0、valid doc validate exit 0、invalid doc validate exit 1
- **main() inspect 各 flag**：--elements、--chunks、--spans、--limit
- **_run_parse / _run_parse_dir**：missing input exit 1、missing dir exit 2、empty dir exit 0+warn、summary 写盘 schema_version/max_chars/recursive/parser_override/files
- **_run_parse_dir 单 txt 文件**：success=1 failure=0
- **模块结构**：所有 _ 前缀 helper 都 callable、_EXTENSION_TO_PARSER 9 项精确

### 撞墙记录
- 初版 1 处 fail：UTF-8 BOM 在 encoding='utf-8' 下不被剥离，导致 JSON 解析失败。改测试期望失败。
  （如要支持 BOM 需 encoding='utf-8-sig'，但 cli 用的 'utf-8'，故 BOM 是错误输入。）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 183 后）：14845 pass / 0 fail / 13 skip（HEAD `58241c9`）

### 下一步建议
- 候选 JG：app/parsers/markdown.py 第七轮
- 候选 JH：app/parsers/html.py 第七轮
- 候选 JI：app/parsers/ipynb.py 第七轮
- 候选 JJ：app/parsers/fallback.py 第七轮
- 候选 JK：app/models.py 第六轮（如还有 gap）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 JG（app/parsers/markdown.py 第七轮）。markdown parser 是常用入口，
第七轮可深入 heading 层级识别、code block 处理、list 嵌套、inline format 提取等。

---


## Round 184（2026-08-05）：app/parsers/markdown_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/markdown_parser.py（326 行，已有 base/edges/edges2-6 共 831 测试）补第七轮
- 深入各 regex 实际匹配行为、section_path 跟踪、各 paragraph 停止条件

### 改动
- 新增 `tests/test_parsers_markdown_edges7.py`（112 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_detect_md_source_type**：大写/混合大小写后缀、未知后缀 raise、无后缀 raise、details 含 suffix
- **_rows_to_md**：空 list 返回 ""、单 row、多 row padding、列对齐填充、pipe 在 edges、分隔符三横
- **_split_pipe_row**：leading/trailing pipe 处理、各 cell strip、单 cell、空串、返回 list
- **_is_pipe_table_start**：i+1 越界 False、首行非 pipe False、分隔行不匹配 False
- **ATX 标题 regex**：1-6 级匹配、7+ # 不匹配、trailing #、无空格不匹配
- **围栏代码块**：language 提取、~~~ fence、空内容 warning、无 end fence 吸收到末尾、内容多行 join
- **主题分隔符 regex**：3+ 字符、更长、含空格、字母不匹配
- **独立图片行 regex**：整行匹配、空 alt、行后/行前有文本不匹配、url 含路径
- **列表项 regex**：-/*/+/ 三种无序、有序 ./)、多位数、无空格不匹配
- **引用块 regex**：> space、>no space、>> nested
- **section_path 跟踪**：多级累积、同级 pop、更高级 pop 多个、无 heading 不出现、heading 元素本身在栈内
- **MarkdownParser 类属性**：name=markdown、version=stdlib/0.1.0、继承 Parser、parse 签名
- **parse 错误路径**：missing file raise ParserError、unsupported_type、OSError → md_read_failed（含 exception_type）
- **parse 编码**：非 UTF-8 用 errors=replace
- **段落停止条件**：每个特殊行类型（heading/fenced/thematic/list/blockquote/image/blank）
- **表格 metadata**：row_count、col_count、source=markdown_pipe_table、content 是 markdown
- **综合**：复杂文档、空文件/纯空白文件 md_no_content warning、element_id 0-padded、confidence=0.95

### 撞墙记录
- 初版 7 处 fail：
  1. _is_pipe_table_start 漏 import → 加到 import 列表
  2. _rows_to_md 单 column 测试期望 3 行实际 4 行（header + sep + 2 body）→ 修正期望
  3. _THEMOMIC_RE_MATCH 拼写错误 + 占位 helper 多余 → 删除，直接调 _THEMATIC_RE
  4. element_ids_zero_padded 用 "para1\npara2"（连续无空行）被识别为单 paragraph → 加空行

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 184 后）：14957 pass / 0 fail / 13 skip（HEAD `5b339da`）

### 下一步建议
- 候选 JL：app/parsers/html_parser.py 第七轮
- 候选 JM：app/parsers/ipynb_parser.py 第七轮
- 候选 JN：app/parsers/text_parser.py 第七轮
- 候选 JO：app/parsers/fallback_parser.py 第七轮
- 候选 JP：app/parsers/base.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 JL（app/parsers/html_parser.py 第七轮）。html parser 也是常用入口，
第七轮可深入 tag 嵌套、attribute 提取、自闭合 tag、entity 解码等。

---


## Round 185（2026-08-05）：app/parsers/html_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/html_parser.py（446 行，已有 base/edges/edges2-6 共 711 测试）补第七轮
- 深入常量精确值、各 tag 处理、表格 cell 边界、字符实体、section_path 跟踪

### 改动
- 新增 `tests/test_parsers_html_edges7.py`（97 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量精确值**：_HEADING_LEVELS 6 项 h1-h6、_SKIP_TAGS 7 项含 script/style/head/title/meta/link/noscript、_HTML_EXTENSIONS (".html",".htm")
- **_detect_html_source_type**：.html/.htm/大写/混合大小写都识别、未知/无后缀/.xml raise、details 含 suffix
- **_rows_to_md**：空 list、单 row、多 row、padding、pipe 在 edges、分隔符三横
- **HtmlParser 类属性**：name=html、version=stdlib/0.1.0、继承 Parser、parse 签名 (self, path, source_hash)
- **_HTMLDocParser 结构**：document_id 存储、elements/warnings 初始空、handle_* 方法 callable、继承 stdlib HTMLParser、convert_charrefs=True
- **<img> 处理**：basic、empty/whitespace src 跳过、missing alt=""、URL 含路径、自闭合、confidence=0.9
- **<pre>/<blockquote>**：basic、保留 newline、嵌套 depth、<p> 在内被忽略、metadata.kind
- **<ul>/<ol>/<li>**：basic、ordered/unordered metadata、嵌套 lists、<li> 不在 list 中默认 ordered=False
- **<br>/<hr>**：br 在 paragraph 加 space、br 外 block 不崩、hr flushes block、hr 单独不崩
- **表格**：basic（th+td 混合）、th-only、空 cells、空 table 无 element、嵌套 table warning、confidence=0.9、<p> 在 cell 文本收集
- **loose text**：在 body 直接成 paragraph、全空白无 element、与 <p> 混合
- **字符实体**：named（&amp;&lt;&gt;）、numeric decimal（&#65;）、numeric hex（&#x41;）、heading/table cell 中
- **section_path 跟踪**：多级累积、同级 pop、高级 pop 多个、heading 元素本身在栈内、无 heading 不出现
- **错误路径**：missing file、unsupported_type、OSError → html_read_failed（含 exception_type）
- **综合**：非 UTF-8 errors=replace、复杂 doc、不规范 markup 不崩、idempotent、element_id 0-padded

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 185 后）：15054 pass / 0 fail / 13 skip（HEAD `b73be03`）

### 下一步建议
- 候选 JQ：app/parsers/ipynb_parser.py 第七轮
- 候选 JR：app/parsers/text_parser.py 第七轮
- 候选 JS：app/parsers/fallback_parser.py 第七轮
- 候选 JT：app/parsers/base.py 第六轮
- 候选 JU：app/parsers/kreuzberg_parser.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 JQ（app/parsers/ipynb_parser.py 第七轮）。ipynb parser 处理 Jupyter notebook，
第七轮可深入 code/markdown cell 混排、outputs 提取、nbformat 边界。

---


## Round 186（2026-08-05）：app/parsers/ipynb_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/ipynb_parser.py（227 行，已有 base/edges/edges2-6 共 744 测试）补第七轮
- 深入 cell source 归一、kernel language 推断、各 cell_type 路径、错误码

### 改动
- 新增 `tests/test_parsers_ipynb_edges7.py`（100 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_IPYNB_EXTENSIONS 常量**：(".ipynb",)，单元素 tuple
- **_detect_ipynb_source_type**：.ipynb/.IPYNB/.Ipynb 都识别、未知/无后缀/.html raise、details 含 suffix
- **_cell_source_to_text 深度**：str 直返、list[str] 拼接、list 含非 str 转 str、None/int/dict 返回空、empty list 返回空
- **_extract_kernel_language 优先级链**：kernelspec.language > kernelspec.name > language_info.name > 空
- **IpynbParser 类属性**：name=ipynb、version=stdlib/0.1.0、继承 Parser、parse 签名
- **parse 错误路径**：missing file、unsupported_type、invalid JSON → ipynb_invalid_json、OSError → ipynb_read_failed、顶层非 dict → ipynb_bad_structure、nbformat<4 → ipynb_unsupported_version（含 nbformat details）、cells 非 list → ipynb_bad_structure
- **parse metadata**：ipynb=True、nbformat、nbformat_minor、cell_count、language
- **markdown cell**：单 cell 多 element（heading + paragraph）、locator 含 cell_index/cell_type/line/section_path、空 cell 无 warning、source 是 list 也工作
- **code cell**：kind=code_cell、language 来自 kernel、content stripped、outputs 丢弃、execution_count 丢弃、空 cell warning（含 cell_index）
- **raw cell**：kind=raw_cell、content stripped、空 cell 跳过无 warning
- **unknown cell type**：warning 含 cell_index/cell_type
- **cell not dict**：warning ipynb_bad_cell
- **element_id 重排**：跳过的 cell 不影响 ID 连续编号、0-padded 4 位
- **markdown 子 warning 透传**：details 含 cell_index
- **section_path cell 间隔离**：每个 markdown cell 独立栈
- **综合**：空 notebook、全空 cell、复杂混排 notebook、idempotent

### 撞墙记录
- 无（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 186 后）：15154 pass / 0 fail / 13 skip（HEAD `915529f`）

### 下一步建议
- 候选 JV：app/parsers/text_parser.py 第七轮
- 候选 JW：app/parsers/fallback_parser.py 第七轮
- 候选 JX：app/parsers/base.py 第六轮
- 候选 JY：app/parsers/kreuzberg_parser.py 第六轮
- 候选 JZ：app/models.py 第六轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 JV（app/parsers/text_parser.py 第七轮）。text parser 是最简单的 parser，
第七轮可深入行号边界、空白处理、encoding 兜底、文件读取路径。

---


## Round 187（2026-08-05）：app/parsers/text_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/text_parser.py（136 行，已有 base/edges/edges2-6 共 543 测试）补第七轮
- 深入 paragraph 切分逻辑、行号边界、各 encoding 路径

### 改动
- 新增 `tests/test_parsers_text_edges7.py`（93 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_TEXT_EXTENSIONS 常量**：(".txt", ".text") 2 项
- **_detect_text_source_type**：.txt/.text/大写/混合都识别、未知/无后缀/.md/.html raise、details 含 suffix（无后缀时 suffix=""）
- **_split_paragraphs 深度**：empty 返回 []、单行、多行单段（\n join）、多段、CRLF/CR only 归一为 LF、前导空白行跳过、尾随空白行忽略、whitespace-only 行视为 blank、多空行作单分隔、line 号 1-indexed、content strip、idempotent、不修改输入
- **TextParser 类属性**：name=text、version=stdlib/0.1.0、继承 Parser、parse 签名
- **parse 错误路径**：missing file（含 path details）、unsupported_type、OSError → text_read_failed（含 exception_type）
- **parse 行为**：单/多 paragraph、多行单段用 \n join、locator line 1-based、element_id 0-padded 4 位递增、confidence=0.95、metadata={}、parent_id/resource_path=None
- **parse metadata**：text=True、source_type=text、source_path 是 str、source_hash/parser_name/parser_version 透传
- **parse 边界**：空文件 → text_no_content warning、whitespace-only → warning、有 content 无 warning、.text 扩展名工作、CRLF/CR only 归一、unicode 内容、非 UTF-8 用 errors=replace 不崩
- **综合**：复杂多段文档、段内空白保留、50 段长文档、idempotent、不修改原文件
- **模块结构**：__all__=["TextParser"]、imports（Path/Any/models/base）、docstring 提及策略/扩展名/不支持事项

### 撞墙记录
- 初版 2 处 fail：source_hash 长度需 = 64（make_document_id 校验），用 "abc123"/"hash1"/"hash2" 会 raise ValueError → 改用 64-char hash

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 187 后）：15247 pass / 0 fail / 13 skip（HEAD `f24260e`）

### 下一步建议
- 候选 KA：app/parsers/fallback_parser.py 第七轮
- 候选 KB：app/parsers/base.py 第六轮
- 候选 KC：app/parsers/kreuzberg_parser.py 第六轮
- 候选 KD：app/models.py 第六轮
- 候选 KE：app/schema.py 第七轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 KA（app/parsers/fallback_parser.py 第七轮）。fallback parser 是 PDF/DOCX 的默认路径，
第七轮可深入 pdfplumber/python-docx 集成、page/bbox 提取、paragraph_index 等。

---


## Round 188（2026-08-05）：app/parsers/fallback_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/fallback_parser.py（630 行，已有 base/edges/edges2-6 共 845 测试）补第七轮
- 深入 _CAPTION_RE 实际匹配、_classify_pdf_paragraph 各路径、_lines_to_para/group_words 聚合、_save_image 写盘

### 改动
- 新增 `tests/test_parsers_fallback_edges7.py`（97 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_CAPTION_RE 实际匹配**：各 prefix（Table/Figure/Fig/表/图）+ 分隔符（./:/、/空格）组合、case insensitive、全角数字、leading whitespace、无数字/无 caption 关键字不匹配、空串不匹配
- **_is_caption**：None/empty 返回 False、返回 bool
- **_rows_to_markdown**：empty/None→''/int cell/uneven padding/单 cell/pipe edges/3 dashes separator
- **_image_filename**：格式 `image_<doc_id_short>_<prefix>_<idx:02d>.<ext>`、doc- 前缀去除、index 2 位 0-padded、custom ext
- **_classify_pdf_paragraph 各路径**：empty→paragraph、caption→caption+heuristic=caption_regex、short（≤80）无句末标点→heading+heuristic=short_line、short 含 ./。/!/!/？→paragraph、> 80→paragraph、80 边界 heading/81 边界 paragraph、caption 优先级 > short
- **_lines_to_para**：empty→text=""bbox=None、单 word、多 word 同行、多行合并、bbox 4 元素 [x0/top/x1/bottom]、同行 word 按 x0 排序、bbox 聚合 min/max
- **_group_words_to_paragraphs**：empty/单 word 返回 list of dict、同 y_center（差 ≤ 3）聚为同行、远 y 仍可同段
- **_save_image 写盘**：自动 mkdir、写 bytes、文件名用 _image_filename、mkdir parents=True、existing dir 不报错、custom ext
- **FallbackParser 类属性**：name=fallback、继承 Parser、__init__(image_output_dir=None)、_image_output_dir 私有属性
- **版本常量**：_PDFPLUMBER_VERSION/_PDFIUM_VERSION/_DOCX_VERSION 存在（None 表示未安装）
- **模块结构**：__all__=["FallbackParser"]、imports（re/Path/Any/models/base）、docstring 提及 pdfplumber/python-docx/kreuzberg

### 撞墙记录
- 初版 4 处 fail：
  1. _classify_pdf_paragraph 用 "Fig 1" 测 caption 优先级，但 regex 要求数字后有分隔符 → 改用 "Fig 1. x"
  2-4. FallbackParser 属性是 `_image_output_dir`（私有），不是 `image_output_dir` → 改测试断言

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 188 后）：15344 pass / 0 fail / 13 skip（HEAD `d1ef6e8`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮
- 候选 KG：app/parsers/kreuzberg_parser.py 第六轮
- 候选 KH：app/models.py 第六轮
- 候选 KI：app/schema.py 第七轮
- 候选 KJ：evaluation/cli.py 第八轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 KF（app/parsers/base.py 第六轮）。base.py 定义 Parser 抽象类、ParserError、make_document_id、detect_source_type，
是所有 parser 的基础，第六轮可深入 detect_source_type 各路径、ParserError 字段、make_document_id 校验。

---

## Round 189（2026-08-05）：app/parsers/kreuzberg_parser.py 第七轮（edges7）

### 目标
- 给 app/parsers/kreuzberg_parser.py（245 行，已有 base/edges/edges2-6 共 803 测试）补第七轮
- 深入 _HEADING_RE 实际匹配、_classify_line 标点边界、_split_content_to_elements 多 block 行为、_make_locator 源类型矩阵

### 改动
- 新增 `tests/test_parsers_kreuzberg_edges7.py`（185 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_HEADING_RE 实际匹配**：match/search/fullmatch 返回 Match/None、group(0)/group(1) 类型、capture group 边界（excludes leading whitespace、includes trailing hashes）、量词字符（{1,6}/.*?/\S）出现在 pattern 源码、6 # 上限、7 # 不匹配、hash+space 必须组合
- **_classify_line 实际行为**：ATX 各 level（1-6）单独覆盖、7 # 退化为 short_line heading、标点 endswith（中间标点不算 terminator，只看末尾）、混合标点（`Hello!World.`）/单字符/单数字、ATX meta 仅含 level+raw_text（无 heuristic）、short_line meta 含 level=0/heuristic=short_line/raw_text
- **_split_content_to_elements 深度**：element_id 格式 `<doc_id>::e<NNNN>`（4 位 0-padded）、双位数（10/100 blocks）编号、heading+body 同 block 拆 2 element、whitespace-only rest 不加 paragraph、连续 heading 共享 para_idx、heading 在 pdf 用 page=1 locator、block 第一行决定类型、内部换行保留（长第一行触发 paragraph 时）
- **_make_locator 源类型矩阵**：pdf keys={page, _kreuzberg_placeholder}、docx keys={paragraph_index, _kreuzberg_heuristic}、text/markdown/html/ipynb/unknown 都走 docx-like 分支、pdf page 恒 1、负数 idx 透传、fresh dict each call
- **_SHORT_LINE_MAX**：值 80、int 类型、用于 _classify_line 阈值（80 heading / 81 paragraph）
- **KreuzbergParser 类属性**：name/version class attr（instance 一致）、继承 Parser、__init__ keyword-only include_document_structure=True 默认、_include_document_structure 私有、positional arg 报 TypeError、两 instance 独立、__dict__ keys 精确（name/version/parse/__init__）、__mro__ 含 Parser、__module__ 正确、parse 签名 (self, path, source_hash)
- **模块级常量**：_KREUZBERG_AVAILABLE（bool）、_KREUZBERG_VERSION（None or str）、_SHORT_LINE_MAX（int 80）、_HEADING_RE（re.Pattern）、try/except ImportError 块结构
- **模块 docstring**：含 kreuzberg/4.10.2/elements/warnings/业务隔离说明
- **一致性**：classify_line 与 split_content_to_elements 判定一致（ATX heading/paragraph/short_line 三类）、block 第一行决定整块类型

### 撞墙记录
- 初版 9 fail + 2 SyntaxWarning：
  1-4. _classify_line 的 endswith 检查只看末尾，"a.b"/"a?b"/"a!b" 中间标点不触发 paragraph → 实际是 short_line heading（修正断言）
  5. ATX with only punctuation 的 meta 检查写成 `meta["heuristic"] not in meta`，应直接 `"heuristic" not in meta`
  6-8. split_content "hello"/"hello world" 是短文本无 terminator → heading（confidence 0.6 + short_line meta），不是 paragraph → 改用 100-char 长文本触发 paragraph
  9. "line1\nline2" 第一行短 → heading，整块 content 是 raw_text "line1"，无内部换行 → 改用长第一行触发 paragraph 保留内部换行
  10-11. 测试函数 docstring 含 `\s`/`\S` 触发 SyntaxWarning → 改 `r"""..."""` raw docstring
- 复发：第一次修文件时把 module docstring 重复粘贴，触发 SyntaxError U+FF08 → 删除重复段落

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 189 后）：15529 pass / 0 fail / 13 skip（HEAD `1cc7de6`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和，514 测试 / 94 行）
- 候选 KG：app/parsers/markdown_parser.py 第八轮（base+edges1-7 共 943 测试 / 326 行）
- 候选 KH：app/parsers/html_parser.py 第八轮（base+edges1-7 共 808 测试 / 446 行）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（base+edges1-7 共 844 测试 / 227 行）
- 候选 KJ：app/parsers/text_parser.py 第八轮（base+edges1-7 共 636 测试 / 136 行）
- 候选 KK：app/parsers/fallback_parser.py 第八轮（base+edges1-7 共 942 测试 / 630 行）
- 候选 KL：app/models.py 第六轮（仍可挖，154 行 / 估计 600+ 测试）
- 候选 KM：app/chunker_legacy.py 或 chunkers/__init__.py（如有）
- 候选 KN：app/pipeline.py 第九轮（base+edges1-8 共 788 测试 / 216 行）
- 候选 KO：evaluation/runner.py 第八轮
- 候选 KP：evaluation/cli.py 第八轮
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KN（app/pipeline.py 第九轮）。pipeline.py 是整套数据流的入口，216 行已有 788 测试覆盖，
第九轮可深入 schema_version 校验、parse 与 chunk 接缝、warnings 去重、error JSON 输出格式等深度边界。

---

## Round 190（2026-08-05）：app/cli.py 第八轮（edges8）

### 目标
- 给 app/cli.py（535 行，已有 base/edges/edges2-7 共 900 测试）补第八轮
- 深入 _run_parse 成功路径、_run_parse_dir 多文件场景、main() 端到端、format_* 各字段边界

### 改动
- 新增 `tests/test_cli_edges8.py`（134 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_run_parse 成功路径**：返回 0、写盘、自动推断信息、--max-chars 覆盖、显式 --parser text、失败时不留半成品 JSON
- **_run_parse_dir 多文件**：全部成功 → 0、任一失败 → 1、summary.files 数量、recursive 子目录遍历、parser override 应用到所有文件、success/failure 计数、file entry 字段（status/input/output/errors）、per-doc JSON 写盘、total == len(files)
- **main() 端到端**：parse 成功返回 0、parse-dir 成功返回 0、parse --max-chars 参数、parse-dir --recursive
- **_format_summary 字段边界**：chunks 0 refs、chunk text with newline、element content=None、element type=None → "None=1"、element types sorted、avg chars、min/max/avg chunk lens、warnings +N more、warnings count、errors count、parser_version=None → "vNone"、source_hash short
- **_format_elements_list**：content empty/None/long truncation、各种 type、+N more message、--limit 0 不显示 more、parent_id empty 不显示、缺 element_id/type → ?
- **_format_chunks_list**：chars=0、refs=0、text with newline、long text truncation、show_spans 各字段（e1[0:5]/e1[?:5]/e1[0:?]/?[0:5]）、empty spans → (none)、more message、limit 0 lists all
- **_load_document_json**：OSError 路径（disk error）、嵌套 dict、空 dict
- **_emit_structured_error extra 类型**：int/list/dict/None/bool/Path（Path → TypeError）
- **_iter_supported_files**：字母序排序、大小写混合都列出、隐藏文件、recursive 列出全部
- **_relative_output_path**：简单文件名、suffix 保留、嵌套子目录、深层嵌套
- **_infer_parser_name**：双 suffix（.tar.gz → fallback）、多点文件名、隐藏文件 .ipynb、仅扩展名（.txt → fallback，因 Path 视为隐藏）
- **_build_arg_parser**：parse parse-dir 各 6 个 parser choices、inspect 4 flags（spans/elements/chunks/limit）、parse-dir --recursive
- **_preview**：默认 width=60、returns str、60 chars 不截断、61 chars 截断、不修改原文、newline 折叠、混合空白、省略号单字符
- **模块结构**：imports（argparse/json/sys/Path/pipeline/future）、utf-8 reconfigure 块、docstring 含 parse/validate/inspect、main guard、无 __all__、_EXTENSION_TO_PARSER 9 keys
- **idempotent**：infer_parser_name/preview/format_summary/format_elements_list/format_chunks_list 多次调用一致

### 撞墙记录
- 初版 6 fail：
  1. element type=None 时 el.get('type', '?') 返回 None（key 存在），type_counts[None]=1 → 改断言到 "None=1"
  2. parser_version=None 同理 → 改断言到 "vNone"
  3. Path 不可 JSON 序列化，json.dumps 抛 TypeError → 改测试为 expect TypeError
  4. Windows Path 排序使用 normcase（大小写不敏感）→ 改测试为 set 比较
  5. str(Path) on Windows 仍用反斜杠 → 改测试为 parent.name == "sub"
  6. Path(".txt").suffix == ""（无主干视为隐藏）→ 改测试为 fallback
- Import 错误：_ExtensionOrStr 是测试文件虚构的、EXTENSION_TO_PARSER 实际是 _EXTENSION_TO_PARSER（带下划线）→ 修正 imports

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 190 后）：15663 pass / 0 fail / 13 skip（HEAD `4475456`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KH：app/parsers/html_parser.py 第八轮（446 行 / 808 测试 = 1.8 tests/line，最低比）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / 844 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / 636 测试）
- 候选 KK：app/parsers/fallback_parser.py 第八轮（630 行 / 942 测试）
- 候选 KL：app/models.py 第六轮（154 行 / 554 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / 943 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / 922 测试，含本批）
- 候选 KO：evaluation/runner.py 第八轮（227 行 / 635 测试）
- 候选 KP：evaluation/cli.py 第八轮（243 行 / 664 测试）
- 候选 KQ：evaluation/metrics.py 第八轮（381 行 / 1103 测试）
- 候选 KR：evaluation/report.py 第七轮（200 行 / 669 测试）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / 821 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KH（app/parsers/html_parser.py 第八轮）。html_parser.py 是当前测试/行比例最低的核心 parser（1.8），
446 行代码有 SAX 复杂状态机（pre/blockquote/table 嵌套、section_path 栈、handle_data 各分支），第八轮可深入未覆盖的内部状态转移。

---

## Round 191（2026-08-05）：app/parsers/html_parser.py 第八轮（edges8）

### 目标
- 给 app/parsers/html_parser.py（446 行，已有 base/edges/edges2-7 共 808 测试，1.8 tests/line 全场最低）补第八轮
- 直接单元测试 _HTMLDocParser 的内部方法（_make_locator_for_current/_emit_image/_flush_block/_reset_block/_start_block）
- 深入 handle_starttag/endtag/data 各分支

### 改动
- 新增 `tests/test_parsers_html_edges8.py`（182 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_HTMLDocParser __init__ 状态**：cur_kind=None、cur_buffer=[]、document_id、elements/warnings 是 list、pre/blockquote/table_depth=0、section_path/levels=[]、list/skip_stack=[]、table_rows_stack=[]、cur_start_line/level=0、cur_ordered=False
- **_make_locator_for_current 直接**：no section → 只 line；with section → 含 section_path "X > Y > Z"；default line=0
- **_make_locator_for_inline 直接**：uses getpos、no section 不含 section_path key
- **_reset_block 直接**：clears cur_kind/buffer、resets level/ordered、不动 section_path
- **_start_block 直接**：sets cur_kind、clears cur_buffer、sets level/ordered、默认 level=0/ordered=False、flush 已有 block、updates cur_start_line
- **_flush_block 直接**：no kind 是 noop、empty text 不 emit、resets after flush、heading/paragraph/list_item/pre/blockquote 各自 metadata、pre → kind=preformatted、blockquote → kind=blockquote、paragraph 无 metadata、confidence 0.95、heading section_path 弹栈逻辑（>= level 全 pop，相同 level 替换，h1 全 pop，append 新层级）、level=0 → max(1,0)=1
- **_emit_image 直接**：appends image element、resource_path=src、metadata={alt}、content=None、confidence 0.9、flushes existing block、element_id 递增、locator 用 inline
- **handle_starttag 各分支**：img dispatch/empty src/missing alt/None alt、br in block/outside、hr flushes、ul/ol push list_stack、li ordered/unordered/no-list-defaults、pre/blockquote nested 不 restart、p in pre/blockquote 忽略、inline tag (b/i/a) 忽略、skip tag push 栈、nested skip、table starts mode、nested table warning + depth 不增
- **handle_endtag 各分支**：p/heading/li 外面无副作用、pre/blockquote clamped to 0、ul/ol pop list_stack、wrong list tag 不 pop、skip stack pop match、unknown tag noop、table ends mode、pre 嵌套外层才 flush
- **handle_startendtag 各分支**：img/br/hr/unknown → dispatch to starttag
- **handle_data 各分支**：in skip stack 忽略、in table cell append、loose text starts paragraph、whitespace only 忽略、in existing block append、各 kind block (heading/list_item/pre/blockquote) 正确 append
- **_rows_to_md 深度**：2x2、1x1、separator 各列 dashes、single body row、no body rows
- **_detect_html_source_type 错误细节**：code=unsupported_type、details 含 suffix、no suffix details.suffix=""
- **HtmlParser 类属性**：name="html"、version="stdlib/0.1.0"、inherits Parser、两实例一致、class attr 不需实例化、不接受 image_output_dir、parse 签名 (self, path, source_hash)
- **模块常量**：_HEADING_LEVELS 6 keys/values、_SKIP_TAGS 7 set、_HTML_EXTENSIONS 2 tuple
- **模块结构**：__all__=["HtmlParser"]、imports、docstring 含 supported/skip/unsupported/source_locator
- **_HTMLDocParser 继承 stdlib**：issubclass(_StdHTMLParser)、convert_charrefs=True、handle_* 方法签名 (self, tag, attrs/data)、init 签名 (self, document_id) 无默认值
- **内部方法存在性**：_make_locator_for_current/_emit_image/_flush_block/_reset_block/_start_block/_handle_table_inner_start/_handle_table_inner_end

### 撞墙记录
- 0 fail：第一次跑全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 191 后）：15845 pass / 0 fail / 13 skip（HEAD `1052ab7`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / 844 测试 = 3.7）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / 636 测试 = 4.7）
- 候选 KK：app/parsers/fallback_parser.py 第八轮（630 行 / 942 测试 = 1.5）
- 候选 KL：app/models.py 第六轮（154 行 / 554 测试 = 3.6）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / 943 测试 = 2.9）
- 候选 KN：app/pipeline.py 第九轮（216 行 / 922 测试 = 4.3）
- 候选 KO：evaluation/runner.py 第八轮（227 行 / 635 测试 = 2.8）
- 候选 KP：evaluation/cli.py 第八轮（243 行 / 664 测试 = 2.7）
- 候选 KQ：evaluation/metrics.py 第八轮（381 行 / 1103 测试 = 2.9）
- 候选 KR：evaluation/report.py 第七轮（200 行 / 669 测试 = 3.3）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / 821 测试 = 3.4）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / 1227 测试 = 3.2）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KK（app/parsers/fallback_parser.py 第八轮）。fallback_parser 是默认 PDF/DOCX 解析路径，
630 行 / 1.5 tests/line 是当前测试密度最低的文件，第八轮可深入 _classify_pdf_paragraph 边界、_lines_to_para
bbox 聚合细节、_group_words_to_paragraphs 聚类阈值、_save_image 各错误路径、FallbackParser.parse 各状态。

---

## Round 192（2026-08-05）：app/parsers/fallback_parser.py 第八轮（edges8）

### 目标
- 给 app/parsers/fallback_parser.py（630 行，已有 base/edges/edges2-7 共 942 测试，1.5 tests/line 当前最低）补第八轮
- 直接单元测试模块级私有函数（_is_heading_style/_extract_inline_image_rids/_group_words_to_paragraphs/_lines_to_para/_classify_pdf_paragraph/_render_pdf_image_region_verbose/_image_filename/_save_image/_rows_to_markdown/_CAPTION_RE/_is_caption）
- 深入 FallbackParser.__init__ 各输入路径

### 改动
- 新增 `tests/test_parsers_fallback_edges8.py`（193 测试 + 1 skip）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_heading_style 全分支**：Title → (True, 1)、Heading 1-9 → (True, N)、Heading 0/clamped、Heading -1/clamped、Heading no-level → (True, 1)、Heading5 (no space after) → (True, 5)、heading lowercase、HEADING uppercase、garbage suffix → (False, 0)、tab separator、empty string → (False, 0)、None → (False, 0)
- **_extract_inline_image_rids**：mock FakeBlip/FakeDrawing/FakeXML classes、no blip → []、single blip → [rId1]、multiple blips、blip embed missing r:embed → skip、empty drawings → []
- **_group_words_to_paragraphs 聚类**：单段（y gap < 3.0 * median_h）、两段（y gap > 1.5 * median_h）、空 list → []、单 word、sorting by y_center then x0、x0 顺序不影响段内
- **_lines_to_para bbox**：min/max aggregation、missing top → default 0.0、missing bottom → default 0.0、单 line、多 line bbox 包含
- **_classify_pdf_paragraph 边界**：caption 优先级（starts_with 图/表/Fig/Figure/Table 匹配 _CAPTION_RE）、80 char 不算 short（→ paragraph）、81 char 短 caption、所有 terminators（。/！/？/./!?/!/?）、纯数字短 → caption？还是 short heading
- **_render_pdf_image_region_verbose unavailable**：pypdfium2 已安装则 skip、unavailable → 返回 str 含 "pypdfium2"
- **_image_filename**：index 0 → "000"、index 5 → "005"、index 50 → "050"、index 999 → "999"、index 1000 → "1000"（4 digits）、no doc- prefix、3-digit zero-padded
- **_save_image**：overwrite 已存在文件、custom extension、path 不存在父目录 → 创建、None image 返回错误字符串
- **_rows_to_markdown**：2x2、1x1、None cell → ""、int cell → str(int)、uneven row lengths、单 row、separator | 包围
- **FallbackParser.__init__**：Path 输入、str 输入（转 Path）、empty str → Path(".")、None image_output_dir → None、tmp_dir 路径、version 常量
- **_CAPTION_RE 实际匹配**：图 1 / 图1 / Fig. 1 / Figure 1 / Table 1 / 表 1、separator 空格/无空格、case-insensitive
- **_is_caption**：直接测试、短文本不长 caption、长文本含关键字 → True
- **模块结构**：__all__=["FallbackParser"]、imports、try/except pypdfium2 ImportError、docstring 含 PDF/DOCX/fallback、version 常量
- **内部函数存在性**：_is_heading_style/_extract_inline_image_rids/_group_words_to_paragraphs/_lines_to_para/_classify_pdf_paragraph/_render_pdf_image_region_verbose/_image_filename/_save_image/_rows_to_markdown/_CAPTION_RE/_is_caption/_parse_pdf/_parse_docx/FallbackParser

### 撞墙记录
- 0 fail：第一次跑全过（193 passed + 1 skipped: pypdfium2 已安装，跳过 unavailable 路径）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 192 后）：16038 pass / 0 fail / 14 skip（HEAD `c3a35cb`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1037 测试 = 4.6）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~829 测试 = 6.1）
- 候选 KL：app/models.py 第六轮（154 行 / ~747 测试 = 4.9）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1136 测试 = 3.5）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1115 测试 = 5.2）
- 候选 KO：evaluation/runner.py 第八轮（227 行 / ~828 测试 = 3.6）
- 候选 KP：evaluation/cli.py 第八轮（243 行 / ~857 测试 = 3.5）
- 候选 KQ：evaluation/metrics.py 第八轮（381 行 / ~1296 测试 = 3.4）
- 候选 KR：evaluation/report.py 第七轮（200 行 / ~862 测试 = 4.3）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / ~1014 测试 = 4.2）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1420 测试 = 3.7）
- 候选 KU：app/schema.py 第七轮（230 行 / ~836 测试 = 3.6）
- 候选 KV：app/chunkers/base.py 第六轮（仍饱和）
- 候选 KW：app/hash_utils.py 第六轮（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KQ（evaluation/metrics.py 第八轮）。metrics.py 是当前测试密度最低的 evaluation/ 文件（3.4），
381 行有 8 类指标（element_count/type/text_preservation/silent_drop/figure_caption/chunk_boundary/
coverage/completeness），第八轮可深入 Counter multisector 边界、divisor=0 reason、ratio macro average、
silent_drop_count manifest expectations 缺失场景。

---

## Round 193（2026-08-05）：evaluation/metrics.py 第八轮（edges8）

### 目标
- 给 evaluation/metrics.py（381 行，已有 base/edges/edges2-7 共 1103 测试）补第八轮
- 直接单元测试模块级私有函数和顶层 compute_automatic_metrics 各分支
- 深入 _is_valid_bbox 拒绝矩阵、_pdf/_docx_locator_ratio locator 多形态、_text_preservation Counter 多集合语义

### 改动
- 新增 `tests/test_evaluation_metrics_edges8.py`（212 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **构造器深度**：_null/reason unicode/empty、_ratio int/float/negative/>1、_bool_metric True/False/0/1/""/None/non-empty string、_int_metric zero/negative/float-coerce/bool-coerce
- **_is_valid_bbox 全面**：4 ints/floats/negatives/3 elements/5 elements/empty/tuple/strings/mixed/bool/single/all-bools/NaN/inf/-inf/None/None-elem/dict
- **_pdf_locator_ratio**：no_elements null、image page-only、paragraph+page+bbox、paragraph no bbox reject、page=0/-1/None/string/float 全 reject、missing source_locator、source_locator=None、mixed valid/invalid (2/3 ratio)、caption requires bbox、header/table/footer page-only、list_item requires bbox、invalid bbox NaN、all-invalid → 0.0
- **_docx_locator_ratio**：no_elements null、7 structural keys 矩阵（section/paragraph_index/run_index/table_index/row_index/col_index/relationship_id）、page/bbox key 拒绝、no structural keys 拒绝、empty locator 拒绝、missing locator 拒绝、mixed 1/3、multiple keys one sufficient
- **_image_resource_ratio**：no_images null、relative + None base_dir → 0.0、filename + base_dir → 1.0、subdir/x.png + base_dir/.name → 1.0、absolute path 忽略 base_dir、3 images mixed 2/3、zero-size 跳过、目录（is_file=False）、OSError caught via monkeypatch、special chars、two-candidates second-ok
- **_chunk_reference_ratio**：empty chunks null、empty list/missing key/None 跳过、valid id、unknown id、multiple ids all valid、partial invalid、mixed 2/4=0.5、empty elements + empty chunks null、empty elements + non-empty chunks → 0.0
- **_strip_unicode_whitespace**：ASCII space/tab/newline/CR/FF/VT、NBSP/em/en/thin/hair/ideographic space、LS/PS、narrow NBSP、empty string、all whitespace、no whitespace、preserves 标点/emoji/CJK/digits、mixed kinds
- **_text_preservation**：equal simple、whitespace ignored、extra chars、missing chars、reorder not equal、duplicate chars（aabb/abab Counter 相同但 sequence 不同）、duplicate mismatch、completely disjoint、both empty null、both whitespace-only null、empty actual / empty expected 各路径、skip image、all images、content None/missing、chunk text None、multiple chunks concat、multiple elements concat、type None treated as text、returns 3 keys
- **_heading_boundary_ratio**：no headings null、first in chunk、not first（=0.0）、id not in chunks、chunks empty list → 0.0、empty ids → 0.0、multiple headings mixed 2/3、duplicate first ids、only paragraphs null
- **_silent_drop_count**：no expectations/empty expectations/empty counts、no drop/actual greater、1 drop/multiple drops、unknown type、actual zero、mixed drop/no-drop、returns int_metric
- **compute_automatic_metrics 顶层**：document=None+error=None、document=None+error with code、error code only、14 metric keys present on failure、minimal valid document、docx locator null for pdf、pdf locator null for docx、other source type both null、no image → null、no chunks → null、no headings → null、no expectations → null、with expectations counts drops、elements missing key defaults []、chunks missing key defaults []、schema_invalid bad doc、schema exception caught (monkeypatch)、error provided with document、by_type unknown/None value、image_base_dir used (keyword)、full text_preservation pipeline
- **模块结构**：_TEXT_TYPES 7 elements/no image、_PDF_BBOX_REQUIRED_TYPES subset/4 elements/excludes table/header/footer、_NOT_EVALUATED constant、__all__ == ["compute_automatic_metrics"]、imports math/Counter/Path/Any、constants are tuples、compute signature 5 params/image_base_dir default None、all internal function signatures、all callable
- **idempotency/不变形**：_is_valid_bbox、_strip_unicode_whitespace、_pdf/_docx/_chunk ratio、compute_automatic_metrics 不变 input、image_resource_ratio 不变 input
- **综合行为**：full pipeline all metric types（heading/paragraph/image/chunks/locator/expectations）、text drop detected、chunk boundary split same chars

### 撞墙记录
- 4 fail（全部测试断言错，非业务代码 bug）：
  1. `test_text_preservation_counter_duplicate_chars`：误判 equal=True，实际 "aabb" vs "abab" 是不同字符串（sequence 等值），但 Counter 交集=1.0
  2. `test_compute_automatic_metrics_by_type_none_value`：dict.get(None, "unknown") 在 key 存在且值为 None 时返回 None（不用 default），所以 by_type[None]=1 而非 by_type["unknown"]
  3. `test_compute_automatic_metrics_image_base_dir_used`：误用位置参数 img_dir 当 expectations → AttributeError（WindowsPath has no .get）；改用 image_base_dir= 关键字
  4. `test_full_pipeline_with_all_metric_types`：同样位置参数错；改用 image_base_dir=
- 修复后 0 fail

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 193 后）：16250 pass / 0 fail / 14 skip（HEAD `556b859`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1100 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KO：evaluation/runner.py 第八轮（227 行 / ~900 测试）
- 候选 KP：evaluation/cli.py 第八轮（243 行 / ~900 测试）
- 候选 KR：evaluation/report.py 第七轮（200 行 / ~900 测试）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / ~1050 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 候选 KV：app/chunkers/base.py 第六轮（仍饱和）
- 候选 KW：app/hash_utils.py 第六轮（仍饱和）
- 候选 KX：evaluation/schema_validation.py 第六轮（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KO（evaluation/runner.py 第八轮）。runner 是 evaluation/ 第二低密度文件（227 行 / ~3.6 tests/line），
第八轮可深入 process_single 各错误路径（parser failure/schema failure/chunker failure）、计时 only_total 策略、
manifest 路径校验、warning 累积逻辑、image 输出目录处理。

---

## Round 194（2026-08-05）：evaluation/runner.py 第八轮（edges8）

### 目标
- 给 evaluation/runner.py（227 行，已有 base/edges/edges2-7 共 635 测试）补第八轮
- 深入 _load_annotation 各 JSON value 类型 + monkeypatch process_single 模拟错误路径
- 验证 run_evaluation public_per_doc 严格剥离私有字段、报告落盘一致、tolerance_chars 传播

### 改动
- 新增 `tests/test_evaluation_runner_edges8.py`（99 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation JSON 多样性**：list/int/string/null/nested dict/empty dict/empty list、BOM（utf-8 不剥 BOM → JSONDecodeError → None）、Unicode 内容、大文件（10k entries）、truncated JSON、extra data、empty file、whitespace only、true/false/float
- **_process_one monkeypatch 路径**：(None, []) → unknown error、(document, [err]) errors 优先 + parser_version=None、(None, [err1, err2]) 取 first、(document, []) 成功 + parser_version 透传、(None, [err]) image_dir=None、失败时 _per_doc 仍 mkdir、失败路径 out_stub 清理、成功 elapsed>0、process_single 参数透传（parser_name/max_chars/write_json）、out_stub 路径含 doc_id、image_dir 用 image_output_dir_for、unlink OSError 静默
- **run_evaluation public_per_doc 剥离私有字段**：_annotation_present / _tolerance_chars / _missing_markers 全部移除、4 个公开 keys (doc_id/source_type/metrics/wall_time_seconds)、wall_time_seconds 含 5 keys (total/parse/chunk/parse_reason/chunk_reason)
- **run_evaluation 报告结构**：6 个顶层 keys (report_version/provenance/devset/summary/per_doc/expected_failures)、report_version == REPORT_VERSION 常量、expected_failures 默认空 list
- **run_evaluation 空场景**：empty manifest → per_doc=[] expected_failures=[]、无 docs 仅 EF、multiple docs
- **run_evaluation parser_version_for_prov**：成功时 set、全部失败时 None、多 doc 取首个成功、provenance parser_name/max_chars 透传
- **run_evaluation 落盘**：file 写入、文件内容与内存对象相等、创建 parent dirs、UTF-8 合法、indent=2
- **run_evaluation tolerance_chars**：默认 30、自定义 100 接受、签名验证
- **run_evaluation metrics 完整集**：14 个 pipeline metrics + 4 个 annotation metrics（figure_caption/chunk_boundary）
- **run_evaluation expected_failures 多场景**：code mismatch、multiple EF、actual_code=None（成功 doc）、actual_code 存在
- **模块结构**：__all__ == ["run_evaluation"]、imports (json/time/Path/Any/process_single/image_output_dir_for/REPORT_VERSION/chunk_boundary_prf/figure_caption_prf/compute_automatic_metrics/aggregate_summary/build_devset_section/build_provenance)、各函数签名与 callable
- **idempotency**：_load_annotation 重复一致、run_evaluation 同输入两跑结构一致
- **综合行为**：text pipeline 完整跑、失败 doc 仍 in per_doc、混合 success/failure、devset/summary/provenance 字段存在、source_type preserved

### 撞墙记录
- 3 fail（全部测试断言错）：
  1. `test_load_annotation_with_bom`：误以为 utf-8 会剥 BOM；实际 encoding='utf-8' 不剥 → JSONDecodeError → None
  2. `test_run_evaluation_file_uses_utf8_with_unicode`：报告里没有 element content（只 metrics），断言 "你好" bytes in raw 不成立；改为验证文件可 UTF-8 解码
  3. `test_run_evaluation_provenance_present`：provenance 没有 "project_root" key（build_provenance 输出含 evaluator_version/git_commit/dependencies 等）；改断言 evaluator_version
- 修复后 0 fail

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 194 后）：16349 pass / 0 fail / 14 skip（HEAD `0835d01`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1100 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KP：evaluation/cli.py 第八轮（243 行 / ~900 测试）
- 候选 KR：evaluation/report.py 第七轮（200 行 / ~900 测试）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / ~1050 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KP（evaluation/cli.py 第八轮）。cli.py 是 evaluation/ 唯一未做 8th round 的入口（243 行 / ~3.5 tests/line），
第八轮可深入 run / validate-report / --manifest 校验、stdout/stderr 输出格式、exit code、各错误码（manifest invalid / report invalid / parser name unknown）。

---

## Round 195（2026-08-05）：evaluation/cli.py 第八轮（edges8）

### 目标
- 给 evaluation/cli.py（243 行，已有 base/edges/edges2-7 共 664 测试）补第八轮
- 深入 _build_parser prog/description/formatter/required=True、各 subparser help/choices/default
- main() 各错误码完整矩阵（manifest 缺失/目录/unknown command/parser 非法/negative max-chars）
- _format_metric 各 value 类型边界（None/bool/float 0.0/int/dict sorted/long name padding/unicode）
- _run_inspect_doc stdout 输出顺序、metric 排序键、source_type 默认、document_id/parser_name 缺失 fallback

### 改动
- 新增 `tests/test_evaluation_cli_edges8.py`（104 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser 深度**：prog=evaluation.cli、description 非空、formatter=RawDescriptionHelpFormatter、subparsers required=True、dest=command、3 个 subcommands、run --manifest/--output required、parser default=fallback choices=(fallback,kreuzberg)、max_chars type=int default=800、tolerance_chars default=30、validate-report input required、inspect-doc input required、help text 含默认值
- **main 错误码矩阵**：no args SystemExit 2、unknown command SystemExit 2、run missing manifest exit 2 + "[ERROR] 清单不存在"、run manifest directory exit 2、validate-report missing exit 2 + "[ERROR] 报告不存在"、validate-report directory exit 2、validate-report invalid JSON exit 1 + "JSON 解析失败"、validate-report empty file exit 1、validate-report list JSON exit 1、inspect-doc missing exit 2 + "文档不存在"、inspect-doc directory exit 2、inspect-doc invalid JSON exit 1、inspect-doc list JSON exit 1 + "JSON 顶层不是对象"、inspect-doc empty dict exit 0、run invalid --parser choice SystemExit 2、run negative max-chars 通过 argparse 走到 manifest 失败
- **_format_metric 类型边界**：None→null、True→"true"、False→"false"、True with custom reason、float 0.123456789→"0.1235" 4 decimal、0.0→"0.0000"、1.0→"1.0000"、int 42、int 0、int -5、dict sorted by key、empty dict、dict with str values、dict with None values、dict with bool values、str default branch、list default branch、long name padded to 36、exact 36 char name、over-36 char name、unicode name
- **_run_inspect_doc 输出**：file/document_id/source/parser/counts/metrics 6 行元信息 + metrics 列表、document_id 缺失→'?'、parser_name 缺失→'v?'、source_type default='unknown'、metric 排序（bool<int<float<dict<null，name 字典序）、null metric 排最后、empty elements/chunks → counts=0、no elements key→默认[]、no chunks key→默认[]、tolerance_chars 传播
- **模块结构**：imports (argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file)、各函数签名 (argv default None/name+metric/args)、return annotation (int/str)、所有 callable
- **idempotency**：_build_parser 两跑独立实例同 prog、_format_metric 同输入同输出、main validate-report missing 两跑同 exit 2
- **综合行为**：inspect-doc 完整 pipeline、via main with tolerance 50、dict mixed int/str/None/bool、argv=None uses sys.argv、image element inspect

### 撞墙记录
- 0 fail：第一次跑全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 195 后）：16453 pass / 0 fail / 14 skip（HEAD `de272df`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1100 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KR：evaluation/report.py 第七轮（200 行 / ~900 测试）
- 候选 KS：evaluation/manifest.py 第八轮（239 行 / ~1050 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/manifest.py 第八轮）。manifest.py 是 evaluation/ 唯一未做 8th round 的核心模块（239 行 / ~4.4 tests/line），
第八轮可深入 path 安全校验（绝对/反斜杠/project_root outside）、expected_failures 加载、annotation_resolved 解析、categories 聚合、manifest schema validation。

---

## Round 196（2026-08-05）：evaluation/manifest.py 第八轮（edges8）

### 目标
- 给 evaluation/manifest.py（239 行，已有 base/edges/edges2-7 共 821 测试）补第八轮
- 深入 _is_absolute_like Windows 盘符边界（digit/underscore/无 separator/单字符/双字符）
- _has_backslash 单字符/混合路径
- _resolve_relative_path field_name 透传到错误消息
- DocumentEntry/ExpectedFailure/Manifest frozen + 10 字段 + properties
- Manifest.content_group_count 自配对/单向/三向链/混合
- load_manifest source_type pdf/docx enum 约束 + monkeypatch schema 跳过

### 改动
- 新增 `tests/test_evaluation_manifest_edges8.py`（132 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like 边界**：empty/单斜杠/POSIX /foo/Windows C:\\/C:/C:foo（无 sep）/lowercase c:\\/单字符 C/双字符 CD/digit 1:\\/underscore _:\\/AB:/`:`/`:/`/相对 ./../z 盘
- **_has_backslash 边界**：a\\b/单 \\/empty/a/b/混合 a/b\\c/多 \\/只 //////尾 \\abc\\
- **_resolve_relative_path 错误消息**：field_name 透传（documents[doc_x].path）、empty/absolute/Windows drive/backslash/outside root/nested outside、valid 返回 Path、嵌套子目录/dot 留 root/dotdot 留 root/resolved 无 ./
- **DocumentEntry frozen**：is_dataclass/frozen setattr raises/10 字段/字段名集合（doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations）/equality/hashable/默认值
- **ExpectedFailure frozen**：is_dataclass/frozen/5 字段/source_type default None/equality/hashable
- **Manifest frozen + properties**：is_dataclass/frozen/5 字段/file_count empty/3、pdf_count/docx_count/other source_type、content_group_count empty/all-unpaired/双向 pair/单向 pair/self pair/混合/两 disjoint pair/三 chain（不同 frozenset 不合并）、categories_covered empty/single/dedup/sorted/unicode/empty tuple
- **load_manifest 完整路径**：file not exists/invalid JSON/manifest_version mismatch（monkeypatch validate 跳过 schema）、empty documents/empty EF、one document/categories/paired_with/sha256/annotation_file/expectations、EF source_type 有/无、path outside root/absolute/backslash 各 raise、project_root explicit str、manifest_path as str
- **_detect_project_root**：from file in root/from nested file/no pyproject（需 file 存在）/directory input/first pyproject in chain
- **模块结构**：__all__ == [ManifestError/Manifest/DocumentEntry/ExpectedFailure/load_manifest]、imports (json/dataclass/Path/Any/MANIFEST_VERSION/validate)、ManifestError issubclass Exception、各函数签名、callable
- **idempotency**：_is_absolute_like/_has_backslash/_resolve_relative_path/load_manifest/DocumentEntry 同输入同输出
- **综合行为**：full pipeline 3 docs + EF + categories + paired_with、properties after load

### 撞墙记录
- 15 fail（全部测试断言/schema 约束错）：
  1. `test_document_entry_field_count`：误以为 9 字段，实际 10（漏数 expectations）
  2. 13 个 load_manifest 测试用 `source_type: "text"`，schema enum 只允许 ["pdf", "docx"]；改用 pdf/docx + 相应后缀
  3. `test_load_manifest_manifest_version_mismatch`：schema 有 `"const": "1.0"`，会先拒绝 "0.0.0"；monkeypatch validate 跳过 schema 才能测后续 version check
  4. `test_detect_project_root_no_pyproject_returns_start`：file 不存在 → `cur.is_file()=False` → cur 不取 parent → 返回 file 路径本身而非 parent；先 write_text 让 file 存在
- 修复后 0 fail

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 196 后）：16585 pass / 0 fail / 14 skip（HEAD `1a88ea9`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1100 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KR：evaluation/report.py 第七轮（200 行 / ~900 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KR（evaluation/report.py 第七轮）。report.py 是 evaluation/ 唯一未做 7th+ round 的核心模块（200 行 / ~4.5 tests/line），
第七轮可深入 aggregate_summary macro average 算法、build_provenance git 信息 fallback、build_devset_section 完整字段、
get_git_provenance 各 OSError 路径。

---

## Round 197（2026-08-05）：evaluation/report.py 第七轮（edges7）

### 目标
- 给 evaluation/report.py（200 行，已有 base/edges/edges2-6 共 669 测试）补第七轮
- 深入 _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量内容
- get_git_provenance 各 subprocess 失败路径（timeout/OSError/SubprocessError/non-zero return/empty stdout）
- get_dependency_versions importlib.metadata 各 PackageNotFoundError 路径
- build_provenance 9 字段集 + max_chars int 强制
- aggregate_summary 完整路径（empty/all-fail/mixed/silent drop）

### 改动
- 新增 `tests/test_evaluation_report_edges7.py`（94 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量内容**：_COUNT_METRICS == ('element_count_total',)、_SUCCESS_BOOL_METRICS == ('pipeline_success',)、_RATIO_METRICS 12 项（schema_valid + 8 ratio + chunk_boundary_{precision,recall,f1}）、排除 figure_caption_/element_count_total/silent_drop_count/pipeline_success、tuple 类型
- **get_git_provenance**：两 keys（git_commit/git_dirty）、真实仓库有 commit、非 git 目录 commit=None dirty=False（subprocess 不抛异常只 non-zero returncode → bool(False and ...)）、OSError safe、SubprocessError safe、TimeoutExpired safe、non-zero returncode 无 commit、empty stdout 无 commit、strip whitespace、porcelain 非空 dirty=True、porcelain 空 dirty=False、status fails dirty=False
- **get_dependency_versions**：3 keys（pdfplumber/python-docx/pypdfium2）、开发环境都装了、PackageNotFoundError → None、generic Exception → None、部分找到部分未
- **build_provenance**：9 keys（git_commit/git_dirty/evaluator_version/report_version/parser_name/parser_version/dependencies/max_chars/run_timestamp_iso）、EVALUATOR_VERSION/REPORT_VERSION 常量、parser_name/version 透传、parser_version None、max_chars int 强制（float 截断/str 数字接受/str 字母 ValueError）、timestamp ISO 格式合法且接近 now、dependencies 是 dict
- **build_devset_section**：6 keys（status/file_count/content_group_count/pdf_count/docx_count/categories_covered）、各字段透传、empty categories、complete status、调用 properties（非字段直接访问）
- **aggregate_summary**：empty 返回 4 keys（counts/success_rates/ratio_macro_averages/silent_drop_total）、各 empty 子结构、单 doc 所有 metric、count 求和（含 skip None）、success_rate（含 rate 计算 + zero division safe + True strict）、ratio macro average（含 skip None + not_evaluated）、silent_drop_total（含 skip None + all None）、metrics 空 dict 安全、metrics 完全缺失抛 KeyError
- **模块结构**：__all__ 5 项、imports (subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION)、各函数签名、return annotation 含 dict、所有 callable
- **idempotency**：get_dependency_versions/aggregate_summary/build_devset_section 重复一致
- **综合行为**：full pipeline 3 docs aggregate、build_provenance 真实仓库跑、metrics 空值处理

### 撞墙记录
- 4 fail（全部测试断言错）：
  1. `test_get_git_provenance_non_git_directory`：误以为非 git 目录 dirty=True；实际 subprocess 不抛异常只返回非零 code，bool(False and ...) = False
  2. `test_get_git_provenance_dirty_when_status_fails`：同上，returncode != 0 时 short-circuit False
  3. `test_build_provenance_max_chars_str_int_coercion`：误以为 int("800") 抛 ValueError；实际 str 数字可被 int() 解析；改用 "abc"
  4. `test_aggregate_summary_metrics_key_missing`：误以为 aggregate_summary 用 .get(metrics, {})；实际直接 r["metrics"]；改为 expect KeyError + 单独测 metrics={}
- 修复后 0 fail

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 197 后）：16679 pass / 0 fail / 14 skip（HEAD `4fc069f`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KI：app/parsers/ipynb_parser.py 第八轮（227 行 / ~1100 测试）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 候选 KV：app/chunkers/base.py 第六轮（仍饱和）
- 候选 KW：app/hash_utils.py 第六轮（仍饱和）
- 候选 KX：evaluation/schema_validation.py 第六轮（仍饱和）
- 候选 KY：evaluation/annotation_metrics.py 第六轮（仍饱和）
- 候选 KZ：evaluation/schema.py 第七轮（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KI（app/parsers/ipynb_parser.py 第八轮）。ipynb_parser.py 是当前未做 8th+ round 的最低密度 parser（227 行 / ~4.6 tests/line），
第八轮可深入 cell_index/cell_type/line locator、code/markdown/raw cell 分类、nbformat 各版本兼容、JSON 结构错误处理。

---

## Round 198（2026-08-05）：app/parsers/ipynb_parser.py 第八轮（edges8）

### 目标
- 给 app/parsers/ipynb_parser.py（227 行，已有 base/edges/edges2-7 共 844 测试）补第八轮
- 深入 _cell_source_to_text 各非 str/list 类型 + list 混合 + 多行
- _extract_kernel_language 各 fallback 优先级（kernelspec.language > kernelspec.name > language_info.name）
- IpynbParser.parse 完整错误矩阵（bad JSON/OSError/top-level/cells/nbformat）
- 单 cell 多 element + element_id 编号 + Document metadata 完整字段

### 改动
- 新增 `tests/test_parsers_ipynb_edges8.py`（117 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_IPYNB_EXTENSIONS**：单元素 tuple (".ipynb",)
- **_detect_ipynb_source_type**：lowercase/uppercase/mixed case 都接受、double extension 取最后段、unknown suffix raise unsupported_type、no suffix raise + message 含 '(无)'、details.suffix 是空字符串
- **_cell_source_to_text**：str/empty str/list/multiline list/empty list/list with int/None/dict、None/int/float/dict/tuple/bool 全返回空、multiline str 保留
- **_extract_kernel_language**：kernelspec.language/kernelspec.name fallback/language 优先于 name/language_info.name/kernelspec 优先于 language_info/empty metadata/None raises AttributeError/kernelspec empty/kernelspec None/无任何 key/all empty/kernelspec empty falls to language_info
- **IpynbParser 类**：name=ipynb/version=stdlib/0.1.0/inherits Parser/parse signature (self/path/source_hash)
- **parse 错误矩阵**：file_not_found/unsupported_type/invalid_json (JSONDecodeError)/top-level list/int (bad_structure)/nbformat 3/2 rejected/nbformat None/4/5 accepted/cells not list/cells missing/cells empty/cell not dict (warning)/unknown cell type (warning + details)
- **parse 各 cell 类型**：markdown cell → multi-elements + locator cell_index/cell_type、code cell → paragraph + metadata kind=code_cell + language、code strips whitespace、code empty warning、raw cell → paragraph + kind=raw_cell、raw strips whitespace、raw empty silently skip
- **element_id**：4-digit zero-padded、跨 cell 递增、document_id 前缀、5-digit at 10000+
- **Document metadata**：ipynb=True/nbformat/nbformat_minor/cell_count/language 5 字段、return Document instance、source_type=ipynb/parser_name=ipynb/chunks=[]/relations=[]/errors=[]、element confidence=0.95/parent_id None
- **多 cell 组合**：mixed cell types、cell_index 跨 skip 保留原 index、markdown heading+paragraph 多 element、markdown sub warning 带 cell_index、code cell list source 拼接
- **模块结构**：__all__/imports/签名/callable
- **idempotency**：detect/cell_source/language/parse 重复一致
- **综合行为**：full pipeline 5 cells、minimal notebook、source list with empty strings、metadata missing kernelspec、metadata None

### 撞墙记录
- 2 fail（测试 bug）：
  1. `test_extract_kernel_language_none_metadata`：函数对 None 不防护，直接 .get() → AttributeError；改 expect AttributeError
  2. `test_parse_metadata_missing_kernelspec`：_make_minimal_notebook 用 `metadata or default`，{} 是 falsy → 被默认值覆盖；改传 truthy 但无 kernelspec 的 dict
- 修复后 0 fail

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 198 后）：16796 pass / 0 fail / 14 skip（HEAD `075e1a7`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KJ：app/parsers/text_parser.py 第八轮（136 行 / ~900 测试）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 候选 KV：app/chunkers/base.py 第六轮（仍饱和）
- 候选 KW：app/hash_utils.py 第六轮（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KJ（app/parsers/text_parser.py 第八轮）。text_parser.py 是当前未做 8th+ round 的最简 parser（136 行 / ~6.6 tests/line），
第八轮可深入 _detect_text_source_type、空文件/无后缀/UTF-8 BOM 处理、单 paragraph 边界字符数、line ending 标准化、metadata 字段。

---

## Round 199（2026-08-05）：app/parsers/text_parser.py 第八轮（edges8）

### 目标
- 给 app/parsers/text_parser.py（136 行，已有 base/edges/edges2-7 共 ~829 测试）补第八轮
- 深入 _detect_text_source_type 各 suffix 组合（txt/text/uppercase/mixed/no-suffix）
- _split_paragraphs 各场景（empty/single line/multi-line/two para/leading-trailing blanks/CR/LF/CRLF 混合/strip/whitespace-only）
- TextParser.parse 错误矩阵（file_not_found/unsupported_type/no suffix）
- element 编号/locator/confidence/metadata/resource_path

### 改动
- 新增 `tests/test_parsers_text_edges8.py`（95 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_TEXT_EXTENSIONS**：(".txt", ".text") 2-tuple
- **_detect_text_source_type**：txt/text/uppercase TXT/TEXT/mixed case、pdf/ipynb/md/docx 拒绝、no suffix 拒绝（details.suffix="" + message 含 '(无)'）、double extension 取最后段
- **_split_paragraphs**：empty string、single line、multi-line 单段、two/three paragraph、leading blank lines（line_no 正确）、trailing blank lines、only blank lines、whitespace-only lines skipped、CRLF/CR 各归一为 LF、混合 CR/LF/CRLF 归一、strip 段首尾、保留段内缩进、no trailing newline、single trailing newline、Unicode、emoji、long paragraph（10k chars）、no blank within、10 段、returns list of tuples
- **TextParser 类**：name="text"/version="stdlib/0.1.0"/inherits Parser/parse signature
- **parse 错误**：file_not_found/unsupported_type (pdf/md/no suffix)
- **parse 成功**：text 扩展名、单段/两段、element_id 编号（4-digit zero-padded + 增量 + document_id 前缀）、type=paragraph、locator line、confidence=0.95、parent_id None、metadata empty、resource_path None、return Document、source_type=text、parser_name=text、parser_version=stdlib/0.1.0、chunks=[]、relations=[]、errors=[]、metadata={text:True}、空文件 warning、whitespace-only warning、UTF-8 unicode、invalid UTF-8 errors=replace、CRLF/CR 各归一、连续空行不膨胀段数、strip whitespace、source_path
- **模块结构**：__all__/imports/签名/callable
- **idempotency**：detect/split/parse 重复一致
- **综合行为**：full pipeline 4 段混合空白、保留缩进代码块、单段无换行、Unicode emoji、locator 归一化行号

### 撞墙记录
- 0 fail：第一次跑全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 199 后）：16891 pass / 0 fail / 14 skip（HEAD `d3f60ab`）

### 下一步建议
- 候选 KF：app/parsers/base.py 第六轮（仍饱和）
- 候选 KL：app/models.py 第六轮（154 行 / ~800 测试）
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 候选 KV：app/chunkers/base.py 第六轮（仍饱和）
- 候选 KW：app/hash_utils.py 第六轮（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KL（app/models.py 第六轮）。models.py 是数据模型核心（154 行 / ~3.6 tests/line），
第六轮可深入 dataclass frozen/Eq/hash 行为、to_dict/from_dict 往返、各字段默认值、Validator 路径。

---

## Round 200（2026-08-05）：app/models.py 第六轮（edges7）

### 目标
- 给 app/models.py（154 行，已有 base/edges/edges2-5 共 ~554 测试）补第六轮
- 深入常量与 Literal 类型集合（SCHEMA_VERSION、ElementType、SourceType）
- 各 dataclass __post_init__ ValueError 边界（empty id / no content+resource / empty source_ids / empty text）
- 默认值不共享（metadata/source_spans/elements 等 default_factory）
- WarningRecord/ErrorRecord details=None 路径与 to_dict 省略键
- Document.to_dict 完整字段集（含 schema_version）+ 嵌套 to_dict
- 模块结构与签名深度（imports/__all__/signature/callable）

### 改动
- 新增 `tests/test_models_edges7.py`（91 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量**：SCHEMA_VERSION="0.1.0"；ElementType 8 值集合；SourceType 6 值集合；排除 unknown/section/rtf
- **Element __post_init__**：empty element_id raises、no content+resource raises（match="必须至少有"）、empty content+no resource raises、only resource_path ok（content=None）、only content ok、both ok
- **Element 默认**：confidence=1.0、parent_id=None、resource_path=None、metadata={}
- **Element metadata 不共享**：default_factory=dict 每实例独立
- **Element to_dict**：8 键集合（element_id/type/source_locator/parent_id/content/resource_path/confidence/metadata）
- **Element 相等/不等/dataclass/字段数=8**
- **Chunk __post_init__**：empty chunk_id raises、empty source_ids raises（match="至少要有一个"）、empty text raises（match="文本不能为空"）、None text raises
- **Chunk 默认**：metadata={}、source_spans=[]，default_factory 独立
- **Chunk to_dict**：5 键集合（chunk_id/text/source_element_ids/metadata/source_spans）
- **Relation**：4 键集合、metadata 不共享、dataclass、字段数=4
- **WarningRecord**：details=None 省略键、details={} 包含键、details={"k":"v"} 包含、默认 None、字段数=3
- **ErrorRecord**：details=None 省略键、details={} 包含、details={"k":"v"} 包含、默认 None、不等 on message、字段数=3
- **Document**：默认 lists 全空、metadata={} 不共享、elements 不共享
- **Document to_dict**：返回 dict、含 schema_version、**13 键**（含 schema_version；schema_version 是 class const，非 dataclass field）
- **Document 字段数=12**（schema_version 不计入 dataclass fields）
- **Document to_dict 嵌套**：elements/chunks/warnings/errors/relations 都 .to_dict()，empty lists
- **Document metadata 引用语义**：to_dict 不深拷贝 metadata，外部修改影响原对象
- **模块结构**：imports（dataclass/field/asdict/typing）、__all__ 未定义（默认 public 全 importable）、to_dict signatures 全 {"self"}、所有 class callable
- **idempotency**：element/chunk/document to_dict 重复调用一致
- **综合行为**：full Document 含所有字段类型、asdict 深拷贝 metadata 嵌套 list

### 撞墙记录
- 2 fail（已修）：
  - `test_document_field_count` 期望 13，实际 12（schema_version 是 class const 不算 dataclass field）→ 改 12
  - `test_document_to_dict_metadata_mutated_not_affecting_source` 期望原对象不变，实际 Document.to_dict 不深拷贝 metadata（外部可变）→ 反向断言

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 200 后）：16982 pass / 0 fail / 14 skip（HEAD `57a5bb7`）

### 下一步建议
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KU：app/schema.py 第七轮（230 行 / ~900 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KU（app/schema.py 第七轮）。schema.py 是 JSON Schema 校验核心（230 行 / ~3.9 tests/line），
第七轮可深入 if/then 条件分支、anyOf、const、enum、自定义错误消息路径、各 source_type 的 locator 校验细节。

---

## Round 201（2026-08-05）：app/schema.py 第七轮（edges7）

### 目标
- 给 app/schema.py（94 行，已有 base/edges/edges2-6 共 ~698 测试）补第七轮
- 深入 SchemaValidationError 异常细节（args、__str__、raise from、errors 默认值 falsy 路径）
- load_schema 编码（UTF-8 BOM）、目录/符号链接/独立返回 dict
- validate 多错误排序、错误 path 深度（elements/chunks/warnings/errors/relations 嵌套）
- is_valid + validate 互验
- validate_file valid 文件往返、UTF-8 中文内容、自定义 schema 走通
- 实际 document.schema.json 各 if/then 条件分支：PDF/DOCX/Markdown/HTML/text/ipynb locator
- $defs 各类型边界（element anyOf、additionalProperties:false、minLength/minimum/minItems/maxItems/const/enum/pattern）

### 改动
- 新增 `tests/test_schema_edges7.py`（165 测试 + 1 skip）
- 仅测试，不动业务代码

### 覆盖要点
- **SchemaValidationError**：args=("m",)、str==message、repr 含类名、errors 默认 []、errors or [] 对 falsy 值（{}/''/0）归一为 []、truthy int 保留、raise from、可 reraise、可附加属性、errors 可变、可被 except Exception 捕获、不被 except ValueError 捕获、init keyword-only、init signature、isinstance Exception、不继承 ValueError/RuntimeError
- **SCHEMA_PATH**：Path 对象、str 尾 document.schema.json、parent.name==schemas、parent.parent==dachuang-autonomous、resolve 幂等、read_bytes 首字节 `{`、read_text 首字符 `{`
- **load_schema**：接受 Path/str、嵌套 dict、array、null、empty object、UTF-8 BOM 抛 JSONDecodeError、目录抛 FileNotFoundError、symlink skip、独立 dict、错误消息含路径、签名默认=SCHEMA_PATH、return annotation 字符串
- **validate 多错误**：空 schema 不约束、schema=true 接受、schema=false 拒绝、type mismatch、required 缺失、按 absolute_path 排序、嵌套 element/chunk/warning/error/relation 路径、schema_path 含 relations/type、message 含 count 与"处"、首错用于 message
- **validate 不变性**：返回 None、不改 document、不改 schema、idempotent、errors 中 path/schema_path 都是 list、count ≥ 1
- **is_valid**：custom schema true/false、default schema valid/invalid、不抛、返回 bool、signature
- **validate_file**：valid 文件往返、invalid 文件抛、None schema 走默认、default schema 检测 missing required、str path、missing 抛 FileNotFoundError、目录抛、invalid JSON 抛 JSONDecodeError、UTF-8 中文、签名
- **if/then 条件分支**：PDF locator 缺 page / page=0 / bbox 4 项 OK / bbox 5/3 项 fail；DOCX 空 {} fail / paragraph_index=0 OK / -1 fail；markdown/html/text locator 缺 line fail / line=1 OK / line+section_path OK；ipynb cell_type 缺/无效/negative cell_index fail
- **element anyOf/additionalProperties**：仅 content OK、仅 resource_path OK、两者共存 OK、都缺 fail、content="" + 无 resource_path fail、额外字段 fail、type enum fail、confidence>1/<0/=0/=1
- **chunk 边界**：空 source_element_ids / 空 chunk_id / 空 text / 空字符串 element_id / source_spans / source_span 负 start / 缺 end / 额外字段
- **relation/warning/error 边界**：metadata / 缺 type / 空 type / 额外字段 / details / 缺 reason / 空 reason / 缺 message
- **顶层字段边界**：schema_version 类型/值、document_id/source_path/parser_name/parser_version 空、source_type unknown、source_hash 大写/短/长/非 hex、elements/chunks/metadata 非数组/非对象、missing required、额外字段允许（顶层无 additionalProperties:false）
- **模块/Draft202012Validator 互操作**：default schema 通过 Draft202012 check、顶层 required 13 项、allOf 6 分支、$defs 12 项、$schema、$id、title、description、element type enum 8 值、source_type enum 6 值
- **模块结构**：__all__ iterable/expected/no-dup/all-exported、_silence_unused_import 私有 callable/返回 None、imports（json/Path/Any/Draft202012Validator）
- **综合行为**：validate→is_valid 一致、full document with all field types 通过、idempotent

### 撞墙记录
- 5 fail（已修）：
  - `test_schema_validation_error_caught_as_value_error_no`：错误地用 pytest.raises(TypeError)，实际 raise SchemaValidationError → 改为 raises(SchemaValidationError)
  - `test_load_schema_signature_return_annotation`：from __future__ annotations 使 annotation 是字符串 → 比较字符串
  - `test_is_valid_signature`：同上，return_annotation=="bool" 而非 is bool
  - `test_validate_file_signature`：同上，return_annotation=="None" 而非 is None
  - `test_validate_error_schema_path_includes_defs`：Draft202012Validator 把 $ref 内联展开，schema_path 不走 $defs 分支 → 改断言含 relations/type

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 201 后）：17147 pass / 0 fail / 15 skip（HEAD `e1baebe`）

### 下一步建议
- 候选 KM：app/parsers/markdown_parser.py 第八轮（326 行 / ~1200 测试）
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KM（app/parsers/markdown_parser.py 第八轮）。markdown_parser 是 Markdown 解析核心（326 行 / ~3.7 tests/line），
第八轮可深入 ATXHeading/ListItem/Table/CodeBlock/FencedCode 各分支、缩进规则、嵌套结构、references 定义。

---

## Round 202（2026-08-05）：app/parsers/markdown_parser.py 第八轮（edges8）

### 目标
- 给 app/parsers/markdown_parser.py（326 行，已有 base/edges/edges2-7 共 ~943 测试）补第八轮
- 深入各正则的边界：_ATX_HEADING_RE（7 hashes/tab 分隔/leading space）
- _THEMATIC_RE（mixed chars/长串）
- _FENCED_RE（4 backticks/lang+-/lang with space）
- _UNORDERED_LIST_RE/_ORDERED_LIST_RE（tab 分隔/0/无 dot paren）
- _BLOCKQUOTE_RE（嵌套 /> > >/> vs 单 / 空格吞 1）
- _STANDALONE_IMAGE_RE（empty alt/嵌套 URL）
- _PIPE_TABLE_ROW_RE/_PIPE_TABLE_SEP_RE（colon 对齐/dash 至少 2）
- _detect_md_source_type（uppercase/MARKDOWN/double ext/(无))
- _rows_to_md（单 cell/uneven/空 body/Unicode）
- _split_pipe_row（无 |/空 cell/strip）
- _is_pipe_table_start（last line/negative index/colon 对齐）
- MarkdownParser 类属性（name/version/inheritance/signature）
- parse() 错误矩阵（file_not_found/unsupported_type/UnicodeDecodeError/OSError）
- parse() 返回值（metadata={markdown:True}/parser_name/version/source_type/source_path）
- _parse_text section_path 栈语义（同级/降级/升 H1 清栈）
- _parse_text 段落中断各分支
- _parse_text fenced code block metadata（kind/language）
- _parse_text blockquote（连续 > 合并/strip）
- _parse_text table（row_count/col_count/source）

### 改动
- 新增 `tests/test_parsers_markdown_edges8.py`（203 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_MD_EXTENSIONS**：(".md", ".markdown") tuple，全小写，前导点
- **_ATX_HEADING_RE**：1-6 个 # 匹配、7 个不匹配、0 个不匹配、无空白不匹配、trailing # 去除、tab 分隔、Unicode 标题、leading space 不匹配
- **_THEMATIC_RE**：3 种字符、mixed 实际匹配、2 个/1 个不匹配、长串、leading/trailing space 不匹配、字母不匹配
- **_FENCED_RE**：3 backticks、4 backticks、3 tildes、lang 含 -/+、lang 空、2 backticks 不匹配、lang 含空格不匹配、混 fence 不匹配
- **_UNORDERED_LIST_RE**：-/*/+ 三种、无 marker/无 space/dot/数字 不匹配、tab 分隔、多词 content
- **_ORDERED_LIST_RE**：1./1) 两种、多位数、0、无 dot/paren 不匹配
- **_BLOCKQUOTE_RE**：> text 与 >text、空 content、嵌套 >>/> > >、\s? 最多吞 1 空格、leading space 不匹配
- **_STANDALONE_IMAGE_RE**：empty alt、URL 含 path、alt 多词、无闭括弧/无 !/无 [] 不匹配
- **_PIPE_TABLE_ROW_RE**：必须前导/尾部 |、单 pipe、空 cells
- **_PIPE_TABLE_SEP_RE**：colon 左/右/两侧、dash < 2 不匹配、字母不匹配、单列不匹配
- **_is_pipe_table_start**：last line False、negative index、3 列、colon 对齐、返回 bool
- **_rows_to_md**：空 list、单行（header+sep）、两行、pad short row、pad first short row、单 cell、Unicode、空 cells
- **_split_pipe_row**：basic、no leading/trailing pipe、无 |、only leading/trailing、strip cells、empty string、returns list、3 cells、empty middle cell
- **_detect_md_source_type**：md/MARKDOWN/Md mixed、double ext、txt/docx/pdf/no suffix raises、details.suffix 正确、message 含 suffix/`(无)`
- **MarkdownParser**：name=markdown、version=stdlib/0.1.0、继承 Parser、parse signature、callable
- **parse() 错误**：file_not_found/unsupported_type/invalid UTF-8 → errors=replace/OSError → md_read_failed
- **parse() 返回**：Document 类型、metadata={markdown:True}、parser_name=markdown、parser_version、source_type=markdown、source_path 是 str、chunks/relations/errors 空 list
- **_parse_text section_path 栈**：单 heading、嵌套 2/3 级、同级 pop、降级 pop 多个、回 H1 清栈、paragraph 继承 section_path、无 heading → locator 仅 line
- **_parse_text 段落中断**：blank line/heading/fenced/thematic/list/blockquote/image/table 各分支
- **_parse_text 段落多行**：\n join 不合并、strip 外部空白
- **list_item metadata**：marker=unordered/ordered、ordered bool、content 提取 strip
- **fenced code metadata**：kind=code_block、language（含空字符串）、empty → warning、no end fence、tilde fence、多行 join
- **blockquote**：单行/多行 join/breaks at non-quote/strip
- **table**：row_count + col_count metadata、content 是 markdown str、单 header+sep 也成立
- **模块结构**：imports（re/Path/Any/Document/Element/WarningRecord/Parser/ParserError/make_document_id）、docstring 含 features 与 unsupported、future annotations
- **综合行为**：full document 含所有 element types、consecutive H1H2H1H2 section_path、idempotent、element_ids 增量 4-digit zero-padded、confidence=0.95、parent_id=None

### 撞墙记录
- 2 fail（已修）：
  - `test_paragraph_breaks_at_fenced_code`：fenced code 本身 type=paragraph，filter 漏掉 → 改用 metadata.kind=None 过滤
  - `test_paragraph_breaks_at_blockquote`：blockquote 也是 type=paragraph → 同上
- 3 SyntaxWarning（已修）：docstring 中 `\w` `\s` 未转义 → 改为 r""" """

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 202 后）：17350 pass / 0 fail / 15 skip（HEAD `cdf8fd1`）

### 下一步建议
- 候选 KN：app/pipeline.py 第九轮（216 行 / ~1200 测试）
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KN（app/pipeline.py 第九轮）。pipeline.py 是编排核心（216 行 / ~5.5 tests/line），
第九轮可深入 run() 各分支、_run_for_file 错误矩阵、source_hash 计算路径、CLI 入口细节。

---

## Round 203（2026-08-05）：app/pipeline.py 第九轮（edges9）

### 目标
- 给 app/pipeline.py（216 行，已有 edges/edges2-8 + errors/helpers 共 ~767 测试）补第九轮
- 深入 get_parser 各返回类型、name 属性、错误消息含全部支持 parser 列表
- image_output_dir_for 各种 source_hash 长度边界（empty/1/15/16/17/64）+ 无 parent 路径
- process_single 错误矩阵深度：hash_io_error / chunker_failed / write_failed / schema_validation_failed
- process_single 写盘行为：write_json=False 不写、output_path=None 不写、嵌套 parent mkdir
- process_single signature：parser_name/max_chars/write_json 是 KEYWORD_ONLY
- validate_only 各种消息格式（OK / missing / JSON 失败 / Schema 失败）
- 模块结构与签名深度

### 改动
- 新增 `tests/test_pipeline_edges9.py`（106 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **get_parser**：每个 name 返回正确类、name 属性、Parser 继承、每次新实例、unknown raises ValueError、错误消息含 6 个支持 parser、含传入名、signature（name/image_output_dir）
- **image_output_dir_for**：None → None、str/Path 都返回 Path、short hash 取全部、empty hash → 目录名 images-、16 char hash、15 char、1 char、path 无 parent、path 含 parent、deep nested、idempotent、signature
- **process_single 错误矩阵**：
  - file_not_found / hash_io_error（monkeypatch compute_file_hash）/ chunker_failed（monkeypatch chunk）
  - schema_validation_failed（monkeypatch validate）+ validation_errors 截断到前 20 条
  - write_failed（monkeypatch json.dump）
  - no_extracted_elements details 含 source_type/warnings、message 含扫描件或 element
  - unexpected_parser_error details 含 parser_name/path
- **process_single 写盘**：write_json=False 不写、output_path=None 不写、嵌套 parent mkdir、UTF-8 内容、indent=2、ensure_ascii=False
- **process_single 不变性**：input file 不变、idempotent
- **process_single 成功**：text/markdown/html/ipynb 各自成功、默认 fallback、默认 max_chars=800、custom max_chars
- **process_single signature**：返回 tuple（2 元）、parser_name 是 KEYWORD_ONLY、max_chars/write_json 也是 KEYWORD_ONLY
- **validate_only**：valid→OK、missing 文件、JSON 失败、Schema 失败、str path、返回 tuple、bool+str 类型、signature
- **模块结构**：__all__ exact、no-dup、future annotations、imports（json/Path/Any/StructuralChunker/compute_file_hash/Document/ErrorRecord/Parser/ParserError/6 个 parser/validate/SchemaValidationError）、docstring 含不变量、无 _silence_unused_import
- **综合行为**：full text pipeline 多 chunk、写盘 JSON 通过 validate_only、4 种 parser 全流程产出 schema 合法 JSON

### 撞墙记录
- 2 fail（已修）：
  - `test_process_single_write_failed_via_monkeypatch`：monkeypatching Path.open 全局导致 compute_file_hash 读文件也失败 → 改 monkeypatch json.dump
  - `test_process_single_default_parser_name_is_fallback`：.txt 文件 fallback parser 不支持，返回 None → 改为 signature 默认值断言

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 203 后）：17456 pass / 0 fail / 15 skip（HEAD `2cf74ad`）

### 下一步建议
- 候选 KT：app/chunkers/structural.py 第九轮（388 行 / ~1450 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 候选 KO：evaluation/cli.py 第九轮（243 行 / ~1000 测试）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT（app/chunkers/structural.py 第九轮）。structural chunker 是分块核心（388 行 / ~3.7 tests/line），
第九轮可深入 _split_text_by_heads、_split_paragraph_by sentences、_split_sentence 长文本边界、source_spans 算法、表/列表元素处理。

---

## Round 204（2026-08-05）：app/chunkers/structural.py 第九轮（edges9）

### 目标
- 给 app/chunkers/structural.py（388 行，已有 base/edges/edges2-8 共 ~1044 测试）补第九轮
- 深入 _WHITESPACE_RE 各类空白（vertical tab/form feed/全角空格 U+3000）
- normalize_text 边界（empty/单字符/Unicode/不修改入参/signature）
- _HARD_BREAK_LANGS 元组精确值与无重复
- _SENTENCE_SPLIT_RE lookbehind 不消耗标点
- _SplitPiece frozen dataclass/字段默认值/hashable
- _hard_split_with_whitespace_fallback 边界（len==max_chars/max_chars+1/window 起止/forced_char 路径）
- _split_long_text 边界（strip 坐标系/拼接不丢字符）
- _PART_* 常量与 sequential 索引
- _ChunkBuffer dataclass/push/length/flush/strategy keyword-only
- StructuralChunker __init__ ValueError 边界（<32/0/负数/1/31）
- chunk() 综合：空 document/heading/table/image/caption 各分支/累积 flush
- _element_text_with_span 各内容形态（leading/trailing/multiline/whitespace only）
- 模块 __all__ / 类属性 / future annotations

### 改动
- 新增 `tests/test_chunker_edges9.py`（153 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_WHITESPACE_RE**：pattern="\s+"、vertical tab/form feed/mixed/collapses to single space、全角空格 U+3000 也匹配、single whitespace 输入→单空格
- **normalize_text**：empty→""、only whitespace→""、单字符、strip 两端、compress internal、\n/\t/中文/punct/Unicode 保留、str 返回、不修改入参、signature
- **_HARD_BREAK_LANGS**：tuple、6 元素、含中英文标点、无重复
- **_SENTENCE_SPLIT_RE**：pattern 含 lookbehind、不消耗标点、多句切分、无空白不切、中文标点+空白切
- **_SplitPiece**：dataclass/frozen/4 字段/text+boundary_after 必填/start+end=0 默认/相等/不等/hashable
- **_hard_split_with_whitespace_fallback**：len==max_chars 单 piece、+1 必切、forced_char 全字母路径、whitespace 在 upper 切、leading whitespace 跳过、trailing rstrip、连续空白跳过、window lower=50、signature、returns list[_SplitPiece]
- **_split_long_text**：==max 单 piece、+1 切、strip 后单 piece、empty→[]、only whitespace→[]、returns list、offsets 在 stripped 坐标、拼接不丢字符（normalize 等价）、每 piece ≤ max_chars、混合短长句
- **_PART_***：4 常量值精确、互异、sequential 索引
- **_ChunkBuffer**：dataclass、3 字段、document_id 必填、parts/counter 默认、独立 per instance、push_text 追加、length 求和、is_empty、flush empty→None、flush only-whitespace→None、flush 返回 Chunk、flush 清空 parts、dedup source_ids、one span per part、text 用单空格 join、metadata strategy/max_chars/char_count、chunk_id 用 document_id::counter、strategy/max_chars keyword-only、init signature
- **StructuralChunker.__init__**：默认 800、显式参数、<32 raises、==32 OK、0 raises、负数 raises、1 raises、错误消息含值、signature
- **chunk()**：空 doc→[]、单 paragraph within max、单 paragraph ==max、chunk_id 4-digit zero-padded、增量、heading 触发 flush、heading 首元素无 prior buf、table isolated、image 跳过（_element_text_with_span 返回空）、caption isolated、长 paragraph sentence split、累积 overflow flush、source_spans 填充（sequential + long）、不修改 document elements、文本保留 normalize 等价
- **_element_text_with_span**：basic、leading/trailing whitespace strip、both ends、only whitespace→empty、empty content→empty、None content→empty、image 强制返回空、multiline 保留 \n、内部空白保留
- **_element_text**：兼容旧接口、返回 text only、image→empty、whitespace only→empty、strip 外部空白
- **模块结构**：__all__ exact={StructuralChunker, normalize_text}、no-dup、imports re/dataclass/field/Any/Chunk/Document/Element、docstring 含 heading/max_chars/source_spans 不变量、future annotations、chunk signature
- **综合行为**：idempotent、full pipeline 含 mixed element types（heading/paragraph/table/caption/list_item）、Unicode+emoji 文本保留

### 撞墙记录
- 7 fail（已修）：
  - `test_normalize_text_signature`：future annotations → return_annotation=="str" 字符串
  - `test_hard_split_consecutive_whitespace_in_input`：错误预期单 piece，实际 2 piece（先 50 a's，后 50 b's，中间空白被吞）
  - `test_chunk_chunk_id_increments`：max_chars=10 < 32 minimum → ValueError；改用 32 + 更长文本
  - `test_chunk_accumulated_overflow_flush`：max_chars=20 < 32；改用 32 + 8-char words（每 4 段 flush）
  - `test_element_text_with_span_empty_content_returns_empty`：Element __post_init__ 拒绝空 content → 改为 whitespace only
  - `test_element_text_returns_empty_for_empty_content`：同上
  - `test_chunker_text_preservation_with_unicode_and_emoji`：max_chars=30 < 32 → 改 50
- 1 SyntaxWarning（已修）：docstring 中 `\s` 未转义 → 改 r""" """

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 204 后）：17609 pass / 0 fail / 15 skip（HEAD `5f6c681`）

### 下一步建议
- 候选 KO：evaluation/cli.py 第九轮（243 行 / ~1000 测试）
- 候选 KP：evaluation/runner.py 第九轮（227 行 / ~1000 测试）
- 候选 KQ：evaluation/metrics.py 第九轮（381 行 / ~1200 测试）
- 候选 KR：evaluation/manifest.py 第九轮（239 行 / ~1100 测试）
- 候选 KS：evaluation/report.py 第八轮（200 行 / ~700 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KO（evaluation/cli.py 第九轮）。evaluation/cli 是 Stage 2 命令入口（243 行 / ~4.1 tests/line），
第九轮可深入 _format_metric 各 type 分支、_run_inspect_doc 输出 ordering、main 错误矩阵边界。

---

## Round 205（2026-08-05）：evaluation/cli.py 第九轮（edges9）

### 目标
- 给 evaluation/cli.py（243 行，已有 base/edges/edges2-8 共 ~768 测试）补第九轮
- 深入 _build_parser 各 argument 属性（type/required/choices/help）
- main() 完整 exit code 矩阵（0/1/2）+ stderr 消息
- _format_metric 各种 type/value/reason 组合（None/bool/float/int/dict/string/list/tuple）
- _run_inspect_doc 输出 ordering（sort_key: bool→0, 数值→1, dict→2, null→3）
- _run_inspect_doc 各种 metrics 组合 + image element 不崩
- main validate-report 成功路径（[OK] 打印）
- 模块结构（imports/__main__/stdout 重配置/no __all__）

### 改动
- 新增 `tests/test_evaluation_cli_edges9.py`（106 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser**：prog=evaluation.cli、description 含中文、subparsers dest=command/required=True、3 个 subcommands、run --manifest/--output required、--parser choices=(fallback, kreuzberg)、--max-chars type=int、--tolerance-chars type=int、所有 default、validate-report/inspect-doc positional input、no args errors、signature
- **_format_metric**：None+reason、None 无 reason（"None" 字面）、bool 小写、bool 默认 'ok'、float 各值（0/1/负/小数截断）、int 各值（0/正/负）、dict 排序、dict int/string 值、空 dict、string、list 走 default、tuple 走 default、name 36 字符 padding、Unicode name、signature、returns str
- **_run_inspect_doc**：returns 0、打印 file/document_id/source/parser/counts/metrics 各行、metrics 排序 bool 在 null 前、各错误返回码（missing=2/dir=2/invalid json=1/non-dict=1）、empty dict 0、source_type=unknown、--tolerance-chars 参数、image element 不崩、pipeline_success 在输出中、signature
- **main() 完整 exit 矩阵**：inspect-doc 0/missing 2、validate-report 0/missing 2/dir 2/invalid json 1/empty 1/list 1/invalid schema 1、run missing manifest 2/dir manifest 2/invalid parser argparse 错误、negative max-chars 通过 argparse、no command errors、unknown command errors、stderr [ERROR] 标签、stderr 含文件名
- **main validate-report 成功路径**：valid report 返回 0、打印 [OK] + 文件名 + Schema 校验
- **main signature / __main__**：argv default None、returns int、main/_build_parser/_format_metric/_run_inspect_doc callable
- **模块结构**：imports（argparse/json/sys/Path/manifest/report/runner/schema）、docstring 含 3 subcommands、future annotations、stdout reconfigure 块、__main__ 入口、无 __all__

### 撞墙记录
- 2 fail（已修）：
  - `test_main_validate_report_valid_returns_0` 与 `prints_filename`：自构造的报告 JSON 不合法（顶层多了 config/evaluator_version/generated_at；silent_drop_total 类型错）
    → 改为符合 evaluation-report.schema.json：仅 report_version/provenance/devset/summary/per_doc，provenance 9 字段、silent_drop_total 类型 integer|null（用 0）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 205 后）：17715 pass / 0 fail / 15 skip（HEAD `2b843d6`）

### 下一步建议
- 候选 KP：evaluation/runner.py 第九轮（227 行 / ~1000 测试）
- 候选 KQ：evaluation/metrics.py 第九轮（381 行 / ~1200 测试）
- 候选 KR：evaluation/manifest.py 第九轮（239 行 / ~1100 测试）
- 候选 KS：evaluation/report.py 第八轮（200 行 / ~700 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/report.py 第八轮）。report.py 是评测报告组装核心（200 行 / ~3.5 tests/line），
第八轮可深入 aggregate_summary 各分支、get_git_provenance subprocess 各错误路径、build_provenance 字段集、build_report 完整字段。

---

## Round 206（2026-08-05）：evaluation/report.py 第八轮（edges8）

### 目标
- 给 evaluation/report.py（200 行，已有 base/edges/edges2-7 共 ~763 测试）补第八轮
- 深入 _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确内容
- EVALUATOR_VERSION / REPORT_VERSION 常量值
- aggregate_summary 各聚合分支（participating_docs/not_evaluated/macro_average）
- aggregate_summary 多文档混合（部分 None / 部分 valid / 部分缺 metric）
- get_git_provenance subprocess 各错误路径（OSError/SubprocessError/TimeoutExpired/不存在目录）
- get_dependency_versions importlib.metadata.PackageNotFoundError
- build_provenance 9 字段精确值 + max_chars 类型强制（int/float/数字字符串）
- build_devset_section 6 字段 + TrackingManifest 验证只读属性
- 模块 imports / __all__ / future annotations

### 改动
- 新增 `tests/test_evaluation_report_edges8.py`（99 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量元组**：_RATIO_METRICS 是 tuple、12 元素、无重复、含 schema_valid/text_preservation_equal/3 个 chunk_boundary/2 个 locator_ratio、排除 figure_caption；_COUNT_METRICS == ("element_count_total",)；_SUCCESS_BOOL_METRICS == ("pipeline_success",)
- **版本常量**：EVALUATOR_VERSION / REPORT_VERSION 是 str、非空、值=="1.1"（本 worktree 不动版本号）
- **aggregate_summary 结构**：4 个 top keys（counts/success_rates/ratio_macro_averages/silent_drop_total）；counts 含 element_count_total；success_rates 含 pipeline_success；ratio_macro_averages 含 12 keys；empty 输入 → silent_drop_total=None、counts sum=None/participating_docs=0、success_rate rate=None/total=0、ratio macro_average=None/participating_docs=0/not_evaluated=0
- **aggregate_summary count 聚合**：3 doc 30 sum、skip None、skip missing metric、participating_docs 准确
- **aggregate_summary success_rate**：全成功 rate=1.0、半成功 rate=0.5、全失败 rate=0.0、skip None value 但 total 仍含全部
- **aggregate_summary ratio macro**：3 doc 0.5 macro、skip None、not_evaluated 准确
- **aggregate_summary silent_drop**：sum、skip None、0 values 仍 count
- **aggregate_summary 类型分离**：counts 不含 ratio；success_rates 不含 ratio；ratio 不含 success
- **get_git_provenance**：返回 dict、keys {git_commit, git_dirty}、real repo commit 是 40 hex、dirty 是 bool、不存在目录 → None+True、OSError/SubprocessError/TimeoutExpired 都安全返回
- **get_dependency_versions**：返回 dict、3 keys（pdfplumber/python-docx/pypdfium2）、value 是 str|None、dev 环境 pdfplumber 与 python-docx 都装了
- **build_provenance**：返回 dict、9 keys、evaluator_version 与 report_version 用模块常量、parser_name/version 传播、parser_version=None OK、max_chars int 强制（int/float/数字字符串）、dependencies 是 dict、run_timestamp_iso ISO 8601 含 T、timestamp 在调用时间附近、git_commit/dirty 与 get_git_provenance 一致
- **build_devset_section**：返回 dict、6 keys、各字段传播、empty categories OK、TrackingManifest 验证只读属性
- **模块结构**：__all__ 5 entries exact、imports（subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION）、docstring 含聚合规则、future annotations
- **综合行为**：idempotent、full pipeline 混合 metrics 正确聚合

### 撞墙记录
- 0 fail：第一次跑全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 206 后）：17814 pass / 0 fail / 15 skip（HEAD `56dfcd8`）

### 下一步建议
- 候选 KP：evaluation/runner.py 第九轮（227 行 / ~1000 测试）
- 候选 KQ：evaluation/metrics.py 第九轮（381 行 / ~1200 测试）
- 候选 KR：evaluation/manifest.py 第九轮（239 行 / ~1100 测试）
- 候选 KT：app/chunkers/structural.py 第十轮（388 行 / ~1600 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KP（evaluation/runner.py 第九轮）。runner.py 是评测运行核心（227 行 / ~4.4 tests/line），
第九轮可深入 _load_annotation JSON 各分支、_process_one 错误矩阵、run_evaluation 公共/私有字段、报告写盘细节。

---

## 2026-08-05 — Round 207（evaluation/runner.py 第九轮）

### 目标
- 给 evaluation/runner.py（227 行，已有 base/edges/edges2-8 共 ~734 测试）补第九轮
- 深入 _load_annotation 各 JSON 类型与错误路径
- _process_one 5 元组返回 / image_dir 派生 / output_root 创建 / unlink 各场景
- run_evaluation 报告结构（6 top keys / per_doc 4 keys / wall_time 5 keys）
- run_evaluation parser_version 第一个成功文档传播
- run_evaluation expected_failures matches True/False
- 报告写盘 UTF-8 / indent=2 / ensure_ascii=False
- 模块 imports / __all__ / future annotations

### 改动
- 新增 `tests/test_evaluation_runner_edges9.py`（79 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation**：None / 不存在 / 目录 / 合法 dict / 空 dict / list / int / string / null / true / false / float / nested dict / empty dict / empty list / invalid JSON / truncated JSON / extra data / empty file / unicode content / 独立 dict（每次新对象）/ 签名（path 唯一参数）
- **_process_one**：返回 5 元组（document_dict/error/total/parser_version/image_dir）；成功路径返回 document_dict + parser_version="0.1.0"；errors 路径 document=None + error dict；无 errors 无 document → unknown code；创建 _per_doc 子目录；total_seconds 是非负 float；image_dir 用 image_output_dir_for（前 16 字符 sha）；image_dir None 当 document=None
- **run_evaluation 报告结构**：返回 dict；keyword-only parser_name/max_chars/tolerance_chars；默认 fallback/800/30；6 top keys（report_version/provenance/devset/summary/per_doc/expected_failures）；report_version 是 str；per_doc 是 list；expected_failures 是 list；summary 4 keys（counts/success_rates/ratio_macro_averages/silent_drop_total）；provenance 9 keys；devset 6 keys
- **run_evaluation 写盘**：写文件到指定路径；UTF-8 编码；indent=2（含 "\n  "）；ensure_ascii=False（中文不转 \uXXXX）；creates parent dirs；返回 dict 与文件 JSON 一致
- **run_evaluation per_doc 私有字段**：公开 per_doc 不含 _annotation_present/_tolerance_chars/_missing_markers；4 公开 keys（doc_id/source_type/metrics/wall_time_seconds）；wall_time 5 keys（total/parse/chunk/parse_reason/chunk_reason）；parse+chunk null + reason=not_instrumented；total 非负
- **run_evaluation provenance 传播**：parser_version 在第一个成功文档后设置；parser_name 传播；max_chars 传播
- **run_evaluation expected_failures**：empty by default；matches=True 当实际 code 等于 expected；matches=False 当实际成功（actual_code=None）；4 keys（doc_id/expected_error_code/actual_error_code/matches）
- **模块结构**：__all__ == ["run_evaluation"]；imports（json/time/Path/Any/process_single/image_output_dir_for/REPORT_VERSION/chunk_boundary_prf/figure_caption_prf/compute_automatic_metrics/aggregate_summary/build_devset_section/build_provenance）；docstring 含 total + not_instrumented + 失败；future annotations；无 _silence_unused_import

### 撞墙记录
- 初版有 1 个 SyntaxError（docstring 含 `\uXXXX` 被 Python 当成 unicode escape 解析失败）→ 改成 raw docstring `r"""..."""`
- 初版 8 fail：_FakeDocEntry 缺 expectations/annotation_resolved 属性（compute_automatic_metrics 调用需要）→ 在 helper __init__ 加上两属性
- 初版 image_dir 测试断言 `images-abc1230000000000`（错误地补 0 到 16 字符）→ 实际是 source_hash[:16]，源串不足 16 时即原值（"abc123"）→ 改断言为 `images-abc123`
- 初版 parser_version_set_on_success 与 expected_failure_mismatch_when_succeeds 用 .txt 文件但 fallback 不支持 .txt（返回 unsupported_type）→ 加 monkeypatch.setattr process_single 返回 _FakeDocument 成功路径

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 207 后）：17893 pass / 0 fail / 15 skip（HEAD `971138e`）

### 下一步建议
- 候选 KQ：evaluation/metrics.py 第九轮（381 行 / ~1200 测试）
- 候选 KR：evaluation/manifest.py 第九轮（239 行 / ~1100 测试）
- 候选 KS：evaluation/annotation_metrics.py 第 N 轮（待查行数）
- 候选 KT：app/chunkers/structural.py 第十轮（388 行 / ~1600 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KQ（evaluation/metrics.py 第九轮）。metrics.py 是评测指标核心（381 行 / ~3.1 tests/line），
第九轮可深入各 ratio/count/success metric 边界、None reason 路径、image_base_dir 各场景。

---

## 2026-08-05 — Round 208（evaluation/metrics.py 第九轮）

### 目标
- 给 evaluation/metrics.py（381 行，已有 base/edges/edges2-8 共 ~1239 测试）补第九轮
- 模块常量精确值（_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED）
- 构造器签名 + 精确 keys
- _is_valid_bbox 穷举矩阵（complex/Decimal/tuple/set/dict/generator/NaN/Inf/bool）
- _pdf_locator_ratio page 类型边界（float/str/bool None）
- _docx_locator_ratio 结构键 7 个逐一验证
- _image_resource_ratio 多图片混合 + 空 resource_path
- _chunk_reference_ratio 各种非 list source_element_ids 形态
- _text_preservation 各 metric 精确值与 null reason
- _heading_boundary_ratio chunk first id 重复
- _silent_drop_count expectations 各形态
- compute_automatic_metrics 13 metric 名精确集合 + 错误码传播
- 模块 imports / __all__ / future annotations

### 改动
- 新增 `tests/test_evaluation_metrics_edges9.py`（215 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块常量**：_NOT_EVALUATED == "not_evaluated"；_TEXT_TYPES 是 tuple / 7 元素 / 不含 image / 无重复；_PDF_BBOX_REQUIRED_TYPES 是 tuple / 4 元素 / 是 _TEXT_TYPES 子集 / 不含 table/header/footer
- **构造器签名**：_null/_ratio/_bool_metric/_int_metric 各 1 参数；return_annotation 是 "dict[str, Any]" 字符串（future annotations）
- **_null**：keys 精确 {value, reason}；value 永远 None；reason 原样保留（含 unicode）
- **_ratio**：keys 精确 {value, reason}；int 输入被强转 float；不做 0..1 截断（-0.5/1.5 原样返回）；reason 永远 None
- **_bool_metric**：keys 精确 {value, reason}；int/str 强转 bool（1→True, 0→False, ""→False, "x"→True）；value 是 bool 类型
- **_int_metric**：keys 精确 {value, reason}；float 强转 int（3.7→3）；bool 强转 int（True→1）；负数保留
- **_is_valid_bbox**：4 ints/floats/mixed/zero/negative/large finite 都 True；None/[]/[1,2,3]/[1,2,3,4,5]/tuple/set/dict/str/[True,...]/[1,2,3,NaN]/[1,2,3,Inf]/[1,2,3,"4"]/None/complex/generator 都 False
- **_pdf_locator_ratio**：empty → null + no_elements；page=0/-1/1.5/"1"/None 全无效；page=True 视为 1 有效（bool 是 int 子类）；非 BBOX 类型（image/table/header/footer）只需 page；BBOX 类型无 bbox 或 bbox 损坏无效；source_locator 缺失/None 视为无效
- **_docx_locator_ratio**：empty → null；section/paragraph_index/run_index/table_index/row_index/col_index/relationship_id 任一单独 valid；page 或 bbox 存在 → invalid；无任何结构键 → invalid；7 个结构键全在仍 valid
- **_image_resource_ratio**：无 image → null + no_image_elements；image 无/空/None resource_path → ratio=0；存在文件 + 非零字节 → valid；零字节文件 → invalid；image_base_dir 用 Path(rp).name 拼接（不是原 rp）
- **_chunk_reference_ratio**：chunks 空 → null + no_chunks；chunk source_element_ids 缺失/None/[] → 该 chunk 计 0；未知 id → 计 0；partial invalid → 计 0；elements 缺 element_id → elem_ids 含 None
- **_strip_unicode_whitespace**：ASCII 空白全删（space/tab/LF/CR/VT/FF）；ZWJ U+200D / soft hyphen U+00AD / BOM U+FEFF 不删（isspace() False）；idempotent
- **_text_preservation**：both empty → equal=True, precision/recall=null+empty_expected_and_actual；expected empty actual 有 → equal=False, precision=0.0, recall=null+empty_expected；expected 有 actual empty → equal=False, precision=null+empty_actual, recall=0.0；image 不入 expected；content None 视为 ""；reorder → equal=False 但 precision/recall=1.0
- **_heading_boundary_ratio**：无 heading → null + no_heading_elements；chunk first id 包含 heading id → valid；不是 first → invalid；空 ids/None/缺字段 chunk 跳过；duplicate first ids 不影响（h1 仍只 matched 一次）
- **_silent_drop_count**：expectations None/{} → null + no_expectations；缺 element_count_by_type → null + no_expectations_element_count；element_count_by_type None/{} → null + no_expectations_element_count；actual ≥ expected → 0；actual < expected → 差值；actual 0 → 全 expected；多 type 求和；int 类型
- **compute_automatic_metrics**：5 参数全部 positional-or-keyword（无 keyword-only）；image_base_dir 默认 None；返回 dict；失败路径 14 keys 精确集合（pipeline_success/error_code/schema_valid + 11 null metric）；error_code 传播；error_code None on success；schema_valid pipeline_failed reason；所有 null metric pipeline_failed reason；docx/pdf locator 按 source_type null；其他 source_type 两个都 null；不修改输入；image_base_dir 参数传播
- **模块结构**：__all__ == ["compute_automatic_metrics"]；imports（math/Counter/Path/Any）；docstring 含纯函数/null/text_preservation；future annotations；无 _silence_unused_import；所有 13 个内部 helper 都在命名空间

### 撞墙记录
- 1 fail：test_pdf_locator_ratio_page_bool_invalid 误以为 page=True 会被拒绝；实际 isinstance(True, int) → True 且 True >= 1 → True，所以 page=True 被接受 → 改成断言 page=True 接受为 1.0（行为记录）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 208 后）：18108 pass / 0 fail / 15 skip（HEAD `de69cec`）

### 下一步建议
- 候选 KR：evaluation/manifest.py 第九轮（239 行 / ~1100 测试）
- 候选 KS：evaluation/annotation_metrics.py 第 N 轮（待查行数）
- 候选 KT：app/chunkers/structural.py 第十轮（388 行 / ~1600 测试）
- 候选 KF/KV/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KR（evaluation/manifest.py 第九轮）。manifest.py 是清单加载/校验核心（239 行 / ~4.6 tests/line），
第九轮可深入 manifest 加载/expectations 校验/expected_failures 解析各边界。

---

## 2026-08-05 — Round 209（evaluation/manifest.py 第九轮）

### 目标
- 给 evaluation/manifest.py（239 行，已有 base/edges/edges2-8 共 ~953 测试）补第九轮
- 模块结构 / __all__ exact / imports 完整集合
- ManifestError 类层级 / args 透传
- DocumentEntry/ExpectedFailure/Manifest 字段类型注解 / frozen
- _is_absolute_like 穷举边界（多字符盘符 / 单字母无 separator / 1 字符 / Unicode）
- _has_backslash 边界
- _resolve_relative_path 返回 Path 实例 / 绝对路径
- load_manifest project_root 接受 Path/str/None
- Manifest properties 类型 / 行为

### 改动
- 新增 `tests/test_evaluation_manifest_edges9.py`（131 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：__all__ == {ManifestError, Manifest, DocumentEntry, ExpectedFailure, load_manifest}（list 5 entries）；imports（json/dataclass/Path/Any/MANIFEST_VERSION/validate）；docstring 含相对路径/绝对路径/正斜杠；future annotations；无 _silence_unused_import；4 个内部 helper 在命名空间
- **ManifestError**：是 class / 是 Exception 子类 / 不是 ValueError/KeyError 子类；可空 args / 多 args 透传；str(e) 返回 message；可被 pytest.raises(ManifestError) 与 pytest.raises(Exception) 捕获
- **DocumentEntry**：是 dataclass；10 字段（doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations）；frozen → setattr 触发 FrozenInstanceError；hashable；equality 按所有字段
- **ExpectedFailure**：是 dataclass；5 字段（doc_id/path_str/resolved_path/expected_error_code/source_type）；frozen；hashable
- **Manifest**：是 dataclass；5 字段（manifest_version/devset_status/documents/expected_failures/project_root）；frozen；hashable
- **Manifest properties**：file_count/pdf_count/docx_count/content_group_count 返回 int；categories_covered 返回 list（sorted + dedup）；empty 时合理默认值
- **_is_absolute_like**：empty/dot/dotdot/filename/2 字符/3 字符无冒号/drive 无 separator（C:foo）/冒号打头（:/foo）/digit drive/underscore drive 都 False；POSIX 绝对/Windows 盘符（C:\、c:/）/Unicode 字母 drive（中:/foo）True
- **_has_backslash**：empty/正斜杠/无反斜杠 False；单/多/首/尾反斜杠 True
- **_resolve_relative_path**：3 参数；返回 Path；返回绝对路径；空/绝对/反斜杠/越界 都抛 ManifestError；field_name 透传到错误消息
- **_detect_project_root**：1 参数；返回 Path；从文件/目录向上找 pyproject.toml；多 pyproject.toml 链取最近；找不到返回 start
- **load_manifest**：2 参数；project_root 默认 None；接受 Path/str 两种 manifest_path；project_root 接受 Path/str；文件不存在/JSON 解析失败抛 ManifestError；返回 Manifest 实例；documents/expected_failures 转 tuple；project_root 已 resolve；manifest_version/devset_status 透传

### 撞墙记录
- 13 fail：_write_manifest 默认 manifest_version="1.1"，但实际 schema const == "1.0"（MANIFEST_VERSION = "1.0"）→ 改默认为 "1.0"
- 1 fail：full_round_trip 测试给 paired_with=None / sha256=None，schema 要求它们是 string → 改成 omit 字段（schema 中两字段都是 optional）
- 同步把测试中所有 "1.1" 替换为 "1.0"（包括 Manifest dataclass 构造、断言 m.manifest_version）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 209 后）：18239 pass / 0 fail / 15 skip（HEAD `efd0fab`）

### 下一步建议
- 候选 KS：evaluation/annotation_metrics.py 第 N 轮（待查行数）
- 候选 KT：app/chunkers/structural.py 第十轮（388 行 / ~1600 测试）
- 候选 KU：evaluation/schema.py 第 N 轮
- 候选 KV：evaluation/schema_validation.py 第 N 轮
- 候选 KF/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT（app/chunkers/structural.py 第十轮）。structural.py 是分块核心（388 行 / ~4.1 tests/line），
第十轮可深入 _split_long_text/_ChunkBuffer/_hard_split_with_whitespace_fallback 更深层边界。

---

## 2026-08-05 — Round 210（app/chunkers/structural.py 第十轮）

### 目标
- 给 app/chunkers/structural.py（388 行，已有 base/edges/edges2-9 共 ~1197 测试）补第十轮
- _SENTENCE_SPLIT_RE 精确分割行为（中英文标点 / 多空白 / 标点 + 非空白）
- _HARD_BREAK_LANGS 元组类型 / 内容 / 无重复
- normalize_text 各空白边界
- _SplitPiece frozen / 默认值 / 字段类型
- _hard_split_with_whitespace_fallback 精确 start/end/boundary_after 坐标
- _split_long_text 多 piece 累积 / 边界
- _ChunkBuffer.flush 各 strategy / counter / source_spans / 去重
- StructuralChunker.chunk 各种 element 顺序组合
- _element_text_with_span 各 content 形态
- 模块结构 / __all__ / 类继承

### 改动
- 新增 `tests/test_chunker_edges10.py`（138 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：__all__ == {StructuralChunker, normalize_text}；imports（re/dataclass/field/Any/Chunk/Document/Element）；docstring 含 heading/max_chars/source_element_id；future annotations；无 _silence_unused_import；4 个内部 helper + 4 个 _PART_* 常量在命名空间
- **_PART_* 常量**：_PART_TEXT=0, _PART_ELEMENT_ID=1, _PART_START=2, _PART_END=3；4 个互异
- **_SENTENCE_SPLIT_RE**：是 re.Pattern；中英文标点 + 空白 切分；标点无空白不切；多空白不产生空 sentence（除非首尾）；空字符串返回 [""]
- **_HARD_BREAK_LANGS**：tuple；6 元素；含中日英 6 个标点（。！？.!?）；全字符串；全单字符；无重复
- **_WHITESPACE_RE**：是 re.Pattern；匹配 space/tab/LF/CR/VT/FF；多空白 sub 成 1
- **normalize_text**：empty → ""；纯空白 → ""；多空白压 1；strip 两端；含 Unicode 空白；idempotent
- **_SplitPiece**：dataclass + frozen；4 字段（text/boundary_after/start/end）；默认 start/end=0；hashable；equality
- **_hard_split_with_whitespace_fallback**：2 参数；返回 list[_SplitPiece]；短文本 1 piece None；前导空白跳过；forced_char 当窗口无空白；whitespace 当窗口有空白；最后 piece None；trailing whitespace rstripped；start/end 在 [0, n]
- **_split_long_text**：2 参数；返回 list[_SplitPiece]；空/纯空白 → []；短 → 1 piece None；先 strip；每 piece ≤ max_chars；len==max_chars → 1 piece；len==max_chars+1 → ≥2 piece；坐标在 stripped text 系
- **_ChunkBuffer**：dataclass 不 frozen；3 字段（document_id/parts/counter）；default_factory 给每实例新 list；push_text 追加 tuple；length=sum(len(text))；is_empty；flush 空返回 None；flush 返回 Chunk；text join space；source_element_ids 去重保序；source_spans 每 part 一项；chunk_id 含 counter 0-pad 4 位；metadata strategy/max_chars/char_count；flush 后清空 parts；whitespace-only text 返回 None
- **StructuralChunker**：是 class；默认 max_chars=800；min 32；<32/0/负数 raise ValueError；chunk() 返回 list[Chunk]；空 document → [];chunk_id 递增 c0000/c0001/...；table 单独 chunk strategy=isolated_table；image 跳过；caption isolated；heading 硬边界；超长 paragraph 用 long_paragraph_sentence_split；不修改 document
- **_element_text_with_span**：image → ("",0,0)；paragraph 含 leading/trailing whitespace → stripped + start/end 偏移；whitespace-only → ("",0,0)；multiline content；签名 (self, el) → tuple[str, int, int]
- **_element_text**：兼容旧接口，返回 stripped text

### 撞墙记录
- 16 fail：Element 与 Document 缺必需字段（source_locator / source_path / parser_name / parser_version）→ sed 批量加 source_locator={} 与 source_path/parser_name/parser_version
- 1 SyntaxWarning：docstring 含 `\s+` 被 Python 当 escape → 用 Python 脚本替换为 r-string + 改写描述
- 1 fail：test_element_text_with_span_none_content_returns_empty 用 content=None 但 Element.__post_init__ 拒绝（要 content 或 resource_path 之一）→ 改成 whitespace-only content 模拟 "effective None"

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 210 后）：18377 pass / 0 fail / 15 skip（HEAD `739af01`）

### 下一步建议
- 候选 KU：evaluation/schema.py 第 N 轮（待查行数）
- 候选 KV：evaluation/schema_validation.py 第 N 轮
- 候选 KW：evaluation/annotation_metrics.py 第 N 轮
- 候选 KX：evaluation/cli.py 第十轮（243 行 / ~1100 测试）
- 候选 KY：evaluation/report.py 第九轮（200 行 / ~860 测试）
- 候选 KF/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW（evaluation/annotation_metrics.py 第 N 轮）。annotation_metrics.py 是 chunk_boundary_prf/figure_caption_prf 核心；
可深入边界 tolerance、最近图片启发式、缺失 annotation 各路径。

---

## 2026-08-05 — Round 211（evaluation/annotation_metrics.py 第八轮）

### 目标
- 给 evaluation/annotation_metrics.py（194 行，已有 base/edges/edges2-7 共 ~532 测试）补第八轮
- 模块结构 / __all__ exact / imports
- PARSER_DOES_NOT_EMIT_RELATIONS 常量值与类型
- figure_caption_prf 各 document/annotation 组合
- chunk_boundary_prf document None / annotation falsy / chunks 不足 2 / anchors 缺失
- chunk_boundary_prf position before/after/unknown/missing
- chunk_boundary_prf marker missing → _missing_markers
- chunk_boundary_prf tolerance_chars 传播 + 软匹配
- chunk_boundary_prf 完美/不对称匹配
- chunk_boundary_prf 不修改输入 / idempotent / 类型

### 改动
- 新增 `tests/test_annotation_metrics_edges8.py`（82 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：__all__ == {PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf}（list 3 entries）；imports（Counter/Any/normalize_text）；docstring 含 figure_caption/chunk_boundary；future annotations；无 _silence_unused_import
- **PARSER_DOES_NOT_EMIT_RELATIONS**：是 str；值 == "parser_does_not_emit_relations"；非空；与模块命名空间引用一致
- **figure_caption_prf**：2 参数（document/annotation）；3 keys 精确（figure_caption_precision/recall/f1）；所有 value=None + reason=parser_does_not_emit_relations；即使 document/annotation 给定仍 null（parser 不出 relation）；idempotent；每 metric 2 keys（value+reason）；不修改输入
- **chunk_boundary_prf 签名**：3 参数（document/annotation/tolerance_chars）；tolerance_chars 是 POSITIONAL_OR_KEYWORD（不是 keyword-only）；默认 30；返回 dict[str, dict[str, Any]]
- **document None 路径**：3 metric null + pipeline_failed；含 _tolerance_chars；4 keys 精确
- **annotation falsy 路径**：None/空 dict/空 list/0 都触发 no_annotation；annotation falsy 时不出现 _missing_markers
- **chunks < 2 路径**：no chunks/1 chunk/缺 chunks 字段/chunks None 都触发 no_predicted_boundaries；1 chunk + 1 anchor → recall=_ratio(0.0)
- **anchors 缺失路径**：annotation 非空但缺 chunk_boundary_anchors → no_ground_truth_anchors；anchors None/空 → no_ground_truth_anchors
- **tolerance_chars 传播**：0/large/42 都写入 _tolerance_chars.value；value 是 int；reason None；2 keys 精确
- **position 边界**：before 用 marker 起始；after 用 marker 结束；unknown/missing 默认 after
- **marker missing**：空 marker/marker 不在 stream → 加入 _missing_markers；value 是 list；reason None；全找到时不出现 _missing_markers
- **完美匹配**：tolerance=0 + 精确位置 → precision/recall/f1=1.0
- **tolerance 软匹配**：距离 ≤ tolerance → matched；距离 > tolerance → 不 matched
- **不对称匹配**：多 prediction 少 anchor → precision 减半；多 anchor 少 prediction → recall 减半（受 missing markers 影响）
- **不变性**：不修改 document/annotation；idempotent；返回新 dict
- **类型**：每 metric 含 value+reason；precision/recall/f1 value 是 float（已评估时）

### 撞墙记录
- 2 fail：
  1. test_chunk_boundary_prf_tolerance_is_keyword_only 误以为 tolerance_chars 是 KEYWORD_ONLY（实际签名 `def chunk_boundary_prf(document, annotation, tolerance_chars=30)` 无 `*` 分隔）→ 改成 POSITIONAL_OR_KEYWORD
  2. test_chunk_boundary_prf_anchors_missing_key 用 `annotation={}` 但空 dict 走 falsy 路径（no_annotation），不是 no_ground_truth_anchors → 改成 `{"other_field": "x"}`（非空但缺 chunk_boundary_anchors）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 211 后）：18459 pass / 0 fail / 15 skip（HEAD `6c08d05`）

### 下一步建议
- 候选 KX：evaluation/cli.py 第十轮（243 行 / ~1100 测试）
- 候选 KY：evaluation/report.py 第九轮（200 行 / ~860 测试）
- 候选 KZ：evaluation/schema.py 第 N 轮
- 候选 KAA：evaluation/schema_validation.py 第 N 轮
- 候选 KF/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX（evaluation/cli.py 第十轮）。cli.py 是评测命令行入口（243 行 / ~4.5 tests/line），
第十轮可深入 _build_parser 各 argument、main exit code、_format_metric 各类型。

---

## 2026-08-05 — Round 212（evaluation/cli.py 第十轮）

### 目标
- 给 evaluation/cli.py（243 行，已有 base/edges/edges2-9 共 ~870 测试）补第十轮
- 模块结构：__all__ 未定义 / imports 完整集合 / __main__ 块 / sys.stdout.reconfigure
- _build_parser：run/validate-report/inspect-doc 各 argument 默认值
- _format_metric：各 reason/value 组合输出格式精确文本
- _run_inspect_doc：各 metric 类型分组 / 排序
- main()：validate-report 完整路径（合法/不存在/目录/JSON 解析失败/schema 不合/非 dict）
- main()：inspect-doc 完整路径（合法/不存在/JSON 失败/非 dict/空 dict/image element）
- main()：run 失败路径（manifest 不存在/目录/非法 parser/非 int max-chars）

### 改动
- 新增 `tests/test_evaluation_cli_edges10.py`（111 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：__all__ 未定义（CLI 入口）；imports（argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file）；docstring 含 run/validate-report/inspect-doc + python -m evaluation.cli；future annotations；无 _silence_unused_import；__main__ 块用 __name__ 守卫 + raise SystemExit；含 reconfigure 块
- **_build_parser**：0 参数；返回 argparse.ArgumentParser；prog == "evaluation.cli"；description 非空；3 个子命令（run/validate-report/inspect-doc）；subparsers dest="command" required
- **run subparser**：--manifest/--output required；--parser choices=(fallback, kreuzberg) default=fallback；--max-chars type=int default=800；--tolerance-chars type=int default=30
- **validate-report subparser**：positional input；无 optional args
- **inspect-doc subparser**：positional input；--tolerance-chars type=int default=30
- **main()**：argv 默认 None；返回 int；无参数 / 未知命令 → SystemExit
- **_format_metric**：返回 str；value None → "null (reason)"；bool True/False → lowercase；float → 4 位小数；int 原样；dict 按 key 排序后渲染 k=v；string/list/tuple 走默认分支；name padding 到 36 字符；name 超 36 不截断；unicode name OK；value=None 时不显示 ok；value 非 None 且 reason=None 时显示 ok
- **_run_inspect_doc**：args 唯一参数；返回 int；callable
- **main validate-report 路径**：合法 → exit 0 + stdout "[OK] filename"；不存在 → exit 2 + stderr [ERROR]；目录 → exit 2；JSON 失败 → exit 1；空文件 → exit 1；schema 不合 → exit 1 + stderr [FAIL]；非 dict（list）→ exit 1
- **main inspect-doc 路径**：合法 → exit 0；输出 file/document_id/source/parser/counts 行；metrics 段；bool metric 排在最前；不存在 → exit 2 + stderr [ERROR]；JSON 失败 → exit 1；非 dict → exit 1；空 dict → exit 0（source_type=unknown）；image element 不崩溃；idempotent；stdout/stderr 分流
- **main run 失败路径**：manifest 不存在 → exit 2 + stderr [ERROR]；manifest 是目录 → exit 2；非法 parser choice → SystemExit 2；非 int max-chars → SystemExit 2；负 max-chars 通过 argparse（manifest 先失败 → exit 2）
- **main 综合行为**：返回 int；argv 各形式都安全

### 撞墙记录
- 1 fail：test_build_parser_has_three_subcommands 误以为 validate-report/inspect-doc 只传 cmd 名即可解析；实际两子命令都要求 positional input → 改成每个子命令传完整 minimal args

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 212 后）：18570 pass / 0 fail / 15 skip（HEAD `0d377a1`）

### 下一步建议
- 候选 KY：evaluation/report.py 第九轮（200 行 / ~860 测试）
- 候选 KZ：evaluation/schema.py 第 N 轮（待查行数）
- 候选 KAA：evaluation/schema_validation.py 第 N 轮（待查行数）
- 候选 KAB：evaluation/__init__.py 第 N 轮（小文件）
- 候选 KF/KW：base.py / chunkers/base.py / hash_utils.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KY（evaluation/report.py 第九轮）。report.py 是评测报告组装核心（200 行 / ~4.3 tests/line），
第九轮可深入 aggregate_summary 各 metric 聚合分支、build_provenance 9 字段、build_devset_section 6 字段。

---

## Round 213 — evaluation/report.py 第九轮（125 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第九轮 edges 测试，覆盖 report 组装、provenance、devset、summary 聚合

### 改动
- 新增 `tests/test_evaluation_report_edges9.py`（125 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块结构**：__all__ 5 entries（get_git_provenance/get_dependency_versions/build_provenance/build_devset_section/aggregate_summary）；imports（subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION）；future annotations；无 _silence_unused_import
- **常量**：_RATIO_METRICS 12 items exact set；_COUNT_METRICS == ("element_count_total",)；_SUCCESS_BOOL_METRICS == ("pipeline_success",)；EVALUATOR_VERSION == "1.1"；REPORT_VERSION == "1.1"
- **get_git_provenance**：signature；返回 dict；真实 repo commit 40 hex；dirty 是 bool；不存在目录 → None + True；monkeypatch subprocess.run TimeoutExpired → None + True；OSError → None + True；SubprocessError → None + True；UTF-8 decode 错误路径
- **get_dependency_versions**：3 keys（pdfplumber/python-docx/pypdfium2）；str|None 值；importlib.metadata.package name 正确
- **build_provenance**：9 keys（evaluator_version/report_version/parser_name/parser_version/max_chars/dependencies/run_timestamp_iso/git/git_dirty）；evaluator/report version 常量；parser_name/version 传播；max_chars int coercion（int/float/str/already-int）；dependencies 3 keys；run_timestamp_iso ISO format + parseable + near now；git commit 40 hex；git_dirty bool
- **build_devset_section**：_FakeManifest 辅助类；6 keys（devset_status/file_count/content_group_count/pdf_count/docx_count/categories_covered）；所有属性传播；categories_covered list 内容完整
- **aggregate_summary**：4 top keys（counts/success_rates/ratio_macro_averages/silent_drop_total）；counts 求和；success_rates 算 rate（True/False/None/mixed）；ratio 各项 macro average；silent_drop_total 求和；type 分离（counts 不在 ratios/success_rates）；idempotent；mixed metrics 完整流水线

### 撞墙记录
- 0 fail：一次通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 213 后）：18695 pass / 0 fail / 15 skip（HEAD `0d79f37`）

### 下一步建议
- 候选 KZ：evaluation/schema.py 第 N 轮（待查行数）
- 候选 KAA：evaluation/schema_validation.py 第 N 轮（待查行数）
- 候选 KAB：evaluation/__init__.py 第 N 轮（小文件）
- 候选 KC：evaluation/runner.py 第十轮（227 行）
- 候选 KD：evaluation/metrics.py 第十轮（381 行）
- 候选 KE：evaluation/manifest.py 第十轮（239 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ 或 KAA，把 evaluation/schema*.py 的覆盖度拉满。

---

## Round 214 — evaluation/runner.py 第十轮（75 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十轮 edges 测试，覆盖 _load_annotation / _process_one / run_evaluation 的新角度

### 改动
- 新增 `tests/test_evaluation_runner_edges10.py`（75 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation 深度**：BOM → None；whitespace-only → None；尾随换行 OK；两个 JSON 对象连写 → None；混合类型数组；深层嵌套；不保持文件句柄；str 路径 → AttributeError
- **_process_one 深度**：parser_version 在成功时取自 document.parser_version；error 时 None；(None, []) 时 None；多个 errors 取 errors[0]；unknown code 路径；unlink OSError 吞掉；out_stub 不存在时跳过 unlink；doc_id 改变 out_stub 名；total_seconds 随 sleep 增加；mkdir idempotent；完整 64 字符 sha → image_dir[:16]
- **run_evaluation 多文档 + 顺序**：per_doc 顺序与 manifest 一致；source_type 传播；parser_version 取首个非 None；多个失败跳过；全部失败 → None；image_base_dir None 当 image_dir 不是目录；image_base_dir 使用当目录存在；missing_markers / tolerance_record default；output_path 接受 str；深层目录创建；output_root idempotent
- **expected_failures 深度**：顺序保留；创建 _per_doc 子目录；actual_error_code 取 errors[0].code；matches 是 bool
- **报告结构**：report_version 来自 REPORT_VERSION 常量；keys 数量 6/4/9/6
- **模块结构**：__all__ 长度 1；docstring 提及 image_dir / write_json / per_doc；imports time.perf_counter；run_evaluation/_load_annotation/_process_one 都 callable；signature 各 param kind 精确；future annotations return_annotation 是 str；process_one return_annotation 含 'tuple'
- **综合**：no_documents 各 section 仍构建；compute_automatic_metrics 每个 doc 调用一次；figure_caption_prf / chunk_boundary_prf 每个 doc 调用一次；tolerance_chars 传播到 chunk_boundary_prf；returned dict == on_disk JSON；_per_dir 在 output_path parent 下

### 撞墙记录
- 1 fail：test_load_annotation_param_optional_via_union 误以为 path 默认 None；实际 _load_annotation(path: Path | None) 无默认值 → 改为 default is Parameter.empty

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 214 后）：18770 pass / 0 fail / 15 skip（HEAD `ff92dcd`）

### 下一步建议
- 候选 KE：evaluation/manifest.py 第十轮（239 行）
- 候选 KD：evaluation/metrics.py 第十轮（381 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KAC：evaluation/cli.py 第十一轮（243 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE（evaluation/manifest.py 第十轮），240 行的核心 IO 模块。

---

## Round 215 — evaluation/manifest.py 第十轮（98 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十轮 edges 测试，覆盖 properties / dataclass 行为 / load_manifest 传播

### 改动
- 新增 `tests/test_evaluation_manifest_edges10.py`（98 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **content_group_count 深度**：0/1/2/3 docs；pair counts as 1；pair+unpaired；单向 pair 仍算 1 组；两个不相交 pair = 2 组；两个 pair + 两个 unpaired = 3 组（实测，pair_ids 算 1，unpaired 算 2）；pair 指向不存在的 doc_id 仍算 1 组；A→B→C 链 = 2 组（不合并）；self pair = 1 组
- **categories_covered**：list 类型；空 list；docs 无 categories；dedup within/across docs；alphabetical sort；unicode；case-sensitive；每次新 list
- **pdf_count / docx_count / file_count**：int 类型；只数对应 source_type
- **Manifest dataclass**：is_dataclass；frozen（FrozenInstanceError）；field count 5；field names exact；equality / inequality；hashable；replace()
- **DocumentEntry 默认值**：sha256/paired_with/annotation_file_str/annotation_resolved 都是 None；categories 默认 ()；expectations 默认 None；frozen；field count 10；field names exact
- **ExpectedFailure 默认值**：source_type None；frozen；field count 5；equality
- **_detect_project_root**：返回 absolute；无 pyproject 时返回 start；文件输入用 parent；深层嵌套；多层 pyproject 取最近
- **_resolve_relative_path**：深层 dotdot；双斜杠 collapse；末尾斜杠；single dot 等于 root；dotdot 跳出 root raises
- **load_manifest 传播**：paired_with；sha256；annotation_file（resolved_path 正确）；expectations；categories 转 tuple；categories 默认 ()；expected_failure source_type；expected_failure source_type 默认 None；resolved_path 绝对；path_str 保留原始；annotation_file 跳出 root raises
- **Schema 边界**：manifest_version 非 1.0 被 Schema const 拒（EvalSchemaError）；devset_status enum 仅 complete/incomplete；additionalProperties False 拒额外键
- **模块结构**：imports MANIFEST_VERSION/validate；ManifestError 是 Exception 子类；不是 ValueError/KeyError 子类；args 透传；__all__ 不暴露内部 helpers；docstring 提及相对路径/项目根；future annotations

### 撞墙记录
- 5 fail：
  1. test_content_group_count_two_pairs_plus_two_unpaired 误算 4；实际 1 pair + 2 unpaired = 3
  2. test_resolve_relative_path_dotdot_to_root 行为矛盾（.. 跳出 root 必抛）；删除该空函数
  3. test_load_manifest_manifest_version_mismatch_raises 期望 ManifestError，实际 Schema const="1.0" 先抛 EvalSchemaError
  4. test_load_manifest_devset_status_variants 用了 schema 不允许的 'partial'/'custom'
  5. test_load_manifest_extra_top_level_keys_ignored 期望 additionalProperties=True；实际 schema=False → 改为 expect EvalSchemaError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 215 后）：18868 pass / 0 fail / 15 skip（HEAD `eb28f6f`）

### 下一步建议
- 候选 KD：evaluation/metrics.py 第十轮（381 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KAC：evaluation/cli.py 第十一轮（243 行）
- 候选 KS：evaluation/runner.py 第十一轮（227 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KD（evaluation/metrics.py 第十轮），最大单文件 381 行，复杂度高。

---

## Round 216 — evaluation/metrics.py 第十轮（97 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十轮 edges 测试，覆盖 helper 函数 / 各 ratio / compute_automatic_metrics 深度

### 改动
- 新增 `tests/test_evaluation_metrics_edges10.py`（97 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_null / _ratio / _bool_metric / _int_metric 深度**：empty string reason；unicode reason；ratio 总 float（即便 int）；ratio NaN/Inf/-0.0；bool_metric with None/list/str/0；int_metric 截断（int(-3.7)=-3）；int_metric string "42"
- **_is_valid_bbox 深度**：0.0 floats；很小的 floats；极大 finite；-0.0；Inf at each position；NaN at each position；3 finite + 1 NaN；float_max / float_min
- **_pdf_locator_ratio 深度**：全空 locator；image only 不需要 bbox；10 个 mixed → 0.5；missing locator key；返回 float
- **_docx_locator_ratio 深度**：locator=None for each；多个结构键仍只算 1；paragraph_index=0 valid；4 mixed elements → 0.5
- **_image_resource_ratio 深度**：5 个 mixed 3 exist → 0.6；image_base_dir filename 匹配；image_base_dir 取 .name 拼接；都不匹配；0 byte file in base_dir；缺 resource_path key
- **_chunk_reference_ratio 深度**：duplicate ids in one chunk；同 id 在多个 chunks；element_id=None；chunks=[] → null；chunk missing field
- **_strip_unicode_whitespace 深度**：中文 ideographic space；em/en space；NBSP；thin space；line/paragraph separator；多种混合；全空白；emoji 保留；digits 保留
- **_text_preservation 深度**：unicode 内容；多 chunk 拼接保序；reorder 破坏 equal 但 precision/recall 仍 1.0；chunk 间加空白 OK；chunk 重复字符 precision=0.5；chunk 缺字符 recall=0.5；image content 排除；返回 keys exact
- **_heading_boundary_ratio 深度**：所有 chunks first id 匹配；chunks empty ids；chunk missing field；多个 chunks 同 first id（set 去重）；heading 无 element_id；no chunks
- **_silent_drop_count 深度**：actual 负数 → drop = exp - actual；actual == exp = 0；actual > exp = 0（max）；unknown expected type 视为 actual=0；多 unknown types 累加
- **compute_automatic_metrics 深度**：source_type=other → 两 locator null；image_base_dir None 时仍校验字符串原值；不 mutate input；完整 14 keys；failure path 11 个 null metrics 都 reason=pipeline_failed；error dict 无 code 键 → KeyError（行为记录）；by_type 含 image；element_count_total 是 int
- **模块结构**：__all__ 仅 compute_automatic_metrics；常量类型正确；docstring 提及纯函数/null/text_preservation

### 撞墙记录
- 2 fail：
  1. test_is_valid_bbox_max_float 用了 `math.float_max if hasattr(...) else sys.float_info.max` 复杂表达式返回 None → 简化为直接 sys.float_info.max
  2. test_compute_automatic_metrics_error_with_dict_no_code_key 期望 error_code=None；实际 error["code"] 抛 KeyError → 改为 expect KeyError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 216 后）：18965 pass / 0 fail / 15 skip（HEAD `b15fce6`）

### 下一步建议
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KAC：evaluation/cli.py 第十一轮（243 行）
- 候选 KS：evaluation/runner.py 第十一轮（227 行）
- 候选 KT：evaluation/manifest.py 第十一轮（239 行）
- 候选 KU：evaluation/annotation_metrics.py 第九轮（194 行）
- 候选 KV：evaluation/report.py 第十轮（200 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KAA + KAB 双小轮（schema_validation.py 第四轮 + __init__.py 第二轮），把 evaluation 小文件全部拉满。

---

## Round 217 — evaluation/annotation_metrics.py 第九轮（74 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第九轮 edges 测试，覆盖 chunk_boundary_prf 各分支

### 改动
- 新增 `tests/test_annotation_metrics_edges9.py`（74 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **figure_caption_prf 深度**：3 keys consistent；reason 一致；value None；ignores annotation content；callable；signature 2 params POSITIONAL_OR_KEYWORD；return annotation 是 str
- **chunk_boundary_prf document/annotation 形态**：document={} 走 no_annotation；document 非空 annotation=None；annotation empty dict；annotation=[] falsy；chunks missing field；chunks zero；chunks one；chunk_boundary_anchors missing；chunk_boundary_anchors None；chunk_boundary_anchors 空列表
- **tolerance_chars**：default 30；POSITIONAL_OR_KEYWORD；写入 _tolerance_chars 各分支都；tolerance=0；tolerance=-1 等价无匹配
- **正常路径**：perfect match after marker；before marker；marker inside chunk；within tolerance；exceeds tolerance no match；f1=0 当 p=r=0；f1 半匹配 ≈ 2/3
- **anchor 字段缺失**：missing marker → '' → missing_markers；missing position 默认 after；unknown position 走 else（after）；anchor not dict → AttributeError
- **多 anchor**：distinct markers；repeated markers advance search_from；marker not in stream recorded in _missing_markers；no _missing_markers key when all found
- **返回 dict 结构**：top keys normal/missing_markers/pipeline_failed/no_annotation/no_predicted/no_ground_truth 各路径精确
- **边界**：chunk text None → empty；missing text field；extra whitespace → normalize；chunks not list → AttributeError；zero chunks；one chunk
- **字段命名**：metric names exact；internal keys prefixed
- **模块结构**：__all__ exact 3；imports Counter/Any/normalize_text/_null/_ratio；常量值与类型；docstring 提及 caption/boundary/tolerance；future annotations

### 撞墙记录
- 1 fail：test_chunk_boundary_prf_chunks_not_a_list 期望函数能跑完；实际 chunks 是 str 时 element 无 .get → AttributeError → 改为 expect AttributeError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 217 后）：19039 pass / 0 fail / 15 skip（HEAD `0159445`）

### 下一步建议
- 候选 KV：evaluation/report.py 第十轮（200 行）
- 候选 KAC：evaluation/cli.py 第十一轮（243 行）
- 候选 KS：evaluation/runner.py 第十一轮（227 行）
- 候选 KT：evaluation/manifest.py 第十一轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KV（evaluation/report.py 第十轮），200 行核心组装模块。

---

## Round 218 — evaluation/report.py 第十轮（112 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十轮 edges 测试，覆盖 provenance/devset/summary 深度

### 改动
- 新增 `tests/test_evaluation_report_edges10.py`（112 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量互斥性**：counts ∩ ratios = ∅；counts ∩ success = ∅；success ∩ ratios = ∅；silent_drop 不在 count/ratio；element_count_total 不在 ratio；schema_valid 在 ratio；pipeline_success 不在 ratio
- **get_git_provenance 深度**：返回 dict 2 keys；callable；POSITIONAL_OR_KEYWORD；无 default；subprocess 调用形式精确（git rev-parse + git status）；TimeoutExpired/OSError/SubprocessError safe；非零 returncode → commit=None；空 stdout → commit=None；strip whitespace；dirty porcelain 非空 True / 空 False
- **get_dependency_versions 深度**：返回 dict；3 keys exact；str|None；callable；0 params；PackageNotFoundError 处理；其他 Exception 处理；真实 pdfplumber 版本
- **build_provenance 深度**：4 params POSITIONAL_OR_KEYWORD；9 keys exact；evaluator/report version 常量；max_chars int type/zero/negative/large/str-digits/float-truncate；parser_name unicode/empty；parser_version propagated/None；dependencies 3 keys；run_timestamp_iso parseable/有时区/near now；git_commit str|None；git_dirty bool
- **build_devset_section 深度**：dict；6 keys；status/file_count/content_group_count/pdf_count/docx_count/categories_covered 都 propagated；empty categories；unicode categories；1 param
- **aggregate_summary 深度**：dict；4 top keys；counts/success_rates/ratio_keys exact；silent_drop_total None for empty；value=0 参与；value=None skip；metric missing skip；success_rates all/none/skip None/empty；ratio macro with zero/skip None/skip missing/all None；silent_drop with zero/skip None/all None/all zero；idempotent；new dict each call
- **模块结构**：__all__ exact 5；imports subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION；EVALUATOR_VERSION/REPORT_VERSION == "1.1"；docstring 提及 counts/success_rates/ratio/silent_drop/不混合；future annotations；_RATIO_METRICS/_COUNT_METRICS/_SUCCESS_BOOL_METRICS 模块级常量存在
- **综合行为**：full pipeline mixed metrics 完整验证；build_provenance 类型一致性

### 撞墙记录
- 0 fail：一次通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 218 后）：19151 pass / 0 fail / 15 skip（HEAD `4de31fe`）

### 下一步建议
- 候选 KAC：evaluation/cli.py 第十一轮（243 行）
- 候选 KS：evaluation/runner.py 第十一轮（227 行）
- 候选 KT：evaluation/manifest.py 第十一轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KAC（evaluation/cli.py 第十一轮），243 行 CLI 入口。

---

## Round 219 — evaluation/cli.py 第十一轮（100 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十一轮 edges 测试，覆盖 _format_metric / _run_inspect_doc / main 各路径

### 改动
- 新增 `tests/test_evaluation_cli_edges11.py`（100 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser 深度**：description 精确；add_help 默认 True；allow_abbrev 默认 True；subparsers required；--help 各子命令都 SystemExit
- **_format_metric 深度**：value=None with specific reason；int 0/负值；very small float → 0.0000；float 0.5 → 0.5000；dict with int/str/0/nested dict/empty string/tuple；list with dict；set/frozenset 走默认；empty reason；name padding 可见；name 超 36 不截断；metric 缺 value/reason key；metric 空 dict；自定义类走默认；value 是 class 走默认
- **_run_inspect_doc 深度**：signature；return annotation；callable；返回 0；prints filename；prints metrics header；missing file → 2；invalid JSON → 1；non-dict → 1；document_id missing → "?"；parser missing → "v?"
- **main() validate-report 深度**：valid returns 0 + prints OK；missing → 2；directory → 2；invalid JSON → 1；empty → 1；invalid schema → 1 + [FAIL]；list/int/string/null/bool/float 顶层都 → 1
- **main() inspect-doc 深度**：empty dict returns 0；prints metrics；source_type unknown when missing；source_type pdf/docx；image element no crash；多 chunks；--tolerance-chars；返回 int；stdout only
- **main() run 深度**：missing manifest → 2；directory manifest → 2；invalid JSON → 1；invalid parser choice → SystemExit 2；non-int max-chars → SystemExit 2；non-int tolerance-chars → SystemExit 2；missing required args → SystemExit
- **模块结构**：__main__ block + raise SystemExit；reconfigure block + try/except + AttributeError/OSError；imports 完整；docstring 提及 run/validate-report/inspect-doc/python -m；future annotations；no _silence_unused
- **综合行为**：no args / unknown command → SystemExit 2；返回 int；custom type 走默认分支

### 撞墙记录
- 0 fail：一次通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 219 后）：19251 pass / 0 fail / 15 skip（HEAD `a734041`）

### 下一步建议
- 候选 KS：evaluation/runner.py 第十一轮（227 行）
- 候选 KT：evaluation/manifest.py 第十一轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KU：evaluation/annotation_metrics.py 第十轮（194 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/runner.py 第十一轮）继续推 evaluation 大文件覆盖。

---

## Round 220 — evaluation/runner.py 第十一轮（49 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十一轮 edges 测试，覆盖 _load_annotation / _process_one / run_evaluation 的新角度

### 改动
- 新增 `tests/test_evaluation_runner_edges11.py`（49 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation 深度**：trailing comma 失败；JSON 注释失败；single quotes 失败；大文件 1000 keys；UTF-8 BOM 失败；UTF-16 编码 → UnicodeDecodeError（不被 except 捕获）；目录 → None；unicode keys；字符串中 escape
- **_process_one 深度**：image_dir 类型；out_stub.parent mkdir；stub unlink after success；error dict 含 code/message；unknown error message 含 process_single 字样；document.to_dict() 被调用；5 tuple 类型一致
- **run_evaluation 深度**：报告 keys 顺序；parser_name 传播；max_chars 0/负值；tolerance_chars 0；private keys 不出现在文件；expectations doc；doc_id 传播；ef doc_id 传播；两个 ef 不同 code；3 个 docs 完整 per_doc；no_docs summary present；devset status/categories/pdf_count/docx_count/file_count/content_group_count 都传播
- **模块结构**：docstring 提及 pipeline/outputs；imports image_output_dir_for；parser_name/max_chars/tolerance_chars KEYWORD_ONLY；manifest/output_path POSITIONAL_OR_KEYWORD；return annotations 含 tuple/None；__all__ 不含 _load_annotation/_process_one
- **综合行为**：no side effects on manifest；public per_doc 不被修改；run idempotent

### 撞墙记录
- 2 fail：
  1. test_load_annotation_utf16_invalid_json 期望 None；实际 UnicodeDecodeError 不被 except 捕 → 改为 expect UnicodeDecodeError
  2. test_run_evaluation_report_file_does_not_contain_private_keys 漏写 monkeypatch fixture 参数 → 加上

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 220 后）：19300 pass / 0 fail / 15 skip（HEAD `287bd07`）

### 下一步建议
- 候选 KT：evaluation/manifest.py 第十一轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KU：evaluation/annotation_metrics.py 第十轮（194 行）
- 候选 KW：evaluation/report.py 第十一轮（200 行）
- 候选 KX：evaluation/cli.py 第十二轮（243 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT（evaluation/manifest.py 第十一轮）继续推 evaluation 大文件。

---

## Round 221 — evaluation/manifest.py 第十一轮（74 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十一轮 edges 测试，覆盖 _is_absolute_like / _has_backslash / load_manifest round-trip

### 改动
- 新增 `tests/test_evaluation_manifest_edges11.py`（74 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like 穷举**：a:/foo True；Z:\foo True；abc False；abcd False；a:b False；a:.foo False；a:-foo False；中:/foo True（unicode letter）；emoji:/foo False；'' False；'/' True；'//' True；网络路径 // True
- **_has_backslash 穷举**：返回 bool；中文 path 无 \ False；中文 path 有 \ True；单字符 '\' True；'/' False；长路径无 / 有 \ True；特殊字符
- **_resolve_relative_path 深度**：深层嵌套目录；unicode 文件名；含空格；含 dot；dotdot 跳出 root raises；多层 dotdot；./ 前缀
- **_detect_project_root 深度**：immediate parent；grandparent；great-grandparent；no pyproject；innermost 优先
- **load_manifest 深度**：7 fields round-trip；expected_failure 完整 round-trip；annotation_file 跨目录；unicode filename；schema 拒绝 missing path/doc_id/source_type；schema 拒 unknown source_type；categories 非 list；path 绝对；path backslash；额外字段被拒
- **Manifest 综合行为**：mixed types；no pdf/docx；only pdf；categories unicode sorted；dedup；all pairs = 2 组
- **模块结构**：ManifestError 多 args；field.type 都是字符串（future annotations）；具体字段类型注解内容；docstring 提及 path 约束

### 撞墙记录
- 0 fail：一次通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 221 后）：19374 pass / 0 fail / 15 skip（HEAD `e778fde`）

### 下一步建议
- 候选 KU：evaluation/annotation_metrics.py 第十轮（194 行）
- 候选 KW：evaluation/report.py 第十一轮（200 行）
- 候选 KX：evaluation/cli.py 第十二轮（243 行）
- 候选 KS：evaluation/runner.py 第十二轮（227 行）
- 候选 KT：evaluation/manifest.py 第十二轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KU（evaluation/annotation_metrics.py 第十轮）继续推 evaluation 大文件。

---

## Round 222 — evaluation/annotation_metrics.py 第十轮（40 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十轮 edges 测试，覆盖大样本/边界值

### 改动
- 新增 `tests/test_annotation_metrics_edges10.py`（40 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **figure_caption_prf 深度**：所有输入相同输出；keys 顺序固定；metric dict keys exact；reason 一致
- **chunk_boundary_prf 大样本**：10 chunks + 1 anchor at end → recall=1, precision=1/9；1 chunk + 多 anchor → no_predicted；2 anchor 1 missing；2 anchor both missing；tolerance=1；tolerance=0；normalize collapses whitespace；punctuation preserved；unicode；repeated chunk text
- **anchor position 边界**：empty marker before/after → missing；position='AFTER'（大写）走 else；position='BEFORE' 走 else（不是 before）；position 是 int 走 else
- **tolerance_chars 写入**：所有路径都写 _tolerance_chars；negative tolerance 无匹配
- **多 predicted / 多 anchor**：predicted 多 → precision<1；anchors 多+部分 missing → recall 不变；predicted 全 out of tolerance
- **返回 dict 结构**：内部键以 _ 前缀；metric keys 无 _ 前缀
- **边界值**：1 chunk + 2 anchors；纯空白 chunk text
- **模块结构**：__all__ 顺序；normalize_text 来自 app.chunkers.structural；_null/_ratio 来自 evaluation.metrics；docstring 提及一对一
- **综合**：keys 跨路径一致；no side effects

### 撞墙记录
- 1 fail：test_chunk_boundary_prf_repeated_chunk_text_two_anchors 误以为两个 anchor 都匹配；实际 num_pred=1（chunk 0 末尾是唯一 boundary），num_gt=2（两个 anchor 都找到），matched=1 → recall=0.5

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 222 后）：19414 pass / 0 fail / 15 skip（HEAD `6ff08f6`）

### 下一步建议
- 候选 KW：evaluation/report.py 第十一轮（200 行）
- 候选 KX：evaluation/cli.py 第十二轮（243 行）
- 候选 KS：evaluation/runner.py 第十二轮（227 行）
- 候选 KT：evaluation/manifest.py 第十二轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW（evaluation/report.py 第十一轮）继续推 evaluation 大文件。

---
## Round 223 — evaluation/report.py 第十一轮（109 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十一轮 edges 测试，覆盖常量元组精确内容、subprocess.run 参数验证、build_provenance 类型转换边界

### 改动
- 新增 `tests/test_evaluation_report_edges11.py`（109 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量元组精确内容**：_RATIO_METRICS 首/尾元素；12 个 ratio name 逐一存在性；figure_caption_* 不在内；doc_id/source_type/wall_time_seconds/error_code 不在内；元组类型不可变；_COUNT_METRICS 与 _SUCCESS_BOOL_METRICS 精确等于单元素元组
- **get_git_provenance 深度**：subprocess.run 调用 kwargs（encoding/errors/timeout=10/cwd/capture_output/text）；调用次数=2；第一次 cmd=rev-parse、第二次 cmd=status --porcelain；真实仓库返回 40 位 hex；返回 dict JSON 可序列化
- **get_dependency_versions 深度**：keys 保留插入顺序（pdfplumber→python-docx→pypdfium2）；逐包调用；混合 found/notfound/exception；importlib.metadata 在函数内 import；JSON 可序列化
- **build_provenance 类型转换边界**：max_chars 从 True/False（int 收为 1/0）；从 None/list/dict 引发 TypeError；从 b'abc' 引发 ValueError；从 b'800' 收为 800；从 '-100' 收为 -100；从 -0.5 收为 0；与 mocked helpers 的集成；dependencies 引用相同 dict；git dict 解构只取 git_commit/git_dirty；evaluator_version 与 evaluation.EVALUATOR_VERSION 是同一对象
- **build_devset_section 深度**：dict key 插入顺序（status 在前，categories_covered 在后）；categories 为 tuple/set 保留；extra attr 忽略；缺 devset_status/categories 抛 AttributeError；None 值透传；负数 file_count 透传；JSON 可序列化
- **aggregate_summary 类型边界**：缺 metrics 抛 KeyError；metrics[key]=None 抛 AttributeError；metrics=list 抛 AttributeError；input=None 抛 TypeError；value=True/False（bool 在 sum 中视为 1/0）；negative values 参与；极大浮点；extra metric keys 忽略；返回 entry keys 精确；输入修改不影响输出；空输入返回 12 个 ratio metrics 全 None；not_evaluated=total-participating；零除保护；顶层 key 顺序
- **综合**：所有 12 ratio metrics 都给值的 macro_average；2 docs all metrics；build_provenance 完整 dict JSON 可序列化；__all__ 名字都是 strings/unique/不含私有常量；顶层 4 keys 顺序

### 撞墙记录
- 0 fail：一次通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 223 后）：19523 pass / 0 fail / 15 skip（HEAD `88d2283`）

### 下一步建议
- 候选 KX：evaluation/cli.py 第十二轮（243 行）
- 候选 KS：evaluation/runner.py 第十二轮（227 行）
- 候选 KT：evaluation/manifest.py 第十二轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和 912 测试/15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和 69 测试/28 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KE：evaluation/annotation_metrics.py 第十一轮（194 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX（evaluation/cli.py 第十二轮）继续推 evaluation 大文件。

---
## Round 224 — evaluation/cli.py 第十二轮（102 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十二轮 edges 测试，覆盖 subparser argument 数量、_format_metric 输出格式精确、_run_inspect_doc print 顺序

### 改动
- 新增 `tests/test_evaluation_cli_edges12.py`（102 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser 深度**：run subparser 5 optional args（不含 help）；validate-report 1 positional；inspect-doc 1 positional + 1 optional；manifest/output required；parser/max-chars/tolerance-chars not required；--parser choices=('fallback','kreuzberg')；默认值精确（max_chars=800, tolerance_chars=30）；prog='evaluation.cli'；epilog=None
- **_format_metric 输出格式精确**：用 Python f-string 构造 expected；None value → `'  {name:36} null  ({reason})'`；bool true/false → `'  {name:36} true/false  (ok)'`；int 0 → `'  {name:36} 0  (ok)'`；float 0.5 → `0.5000`；NaN/Inf fallthrough；bytes/bytearray/complex/range/set/frozenset fallthrough；dict sorted alphabetically；dict 含 int keys；dict 含 negative int values；dict 含 float values；reason 含括号；reason 长字符串；每行 '  ' 开头；name 字段 width=36
- **_run_inspect_doc 深度**：tolerance_chars=0/negative 不崩；不写文件（mtime 不变）；4 行 header（file/document_id/source/parser/counts）；空行+metrics: 头；elements=N chunks=M 输出；metric 行缩进；缺 parser_name/source_path 显示 '?'；source_type 缺显示 'unknown'；多余 keys 不出错；elements=None 显式触发 TypeError（compute_automatic_metrics 用 `.get('elements', [])` 拿到 None）
- **main 综合行为**：各 return code 是 int；validate-report 成功路径打印 '[OK]' 到 stdout、'[FAIL]' 到 stderr、'[ERROR]' 到 stderr；完整 inspect-doc 流程验证 stdout
- **模块结构**：argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file 都 import；4 个 callable；docstring 含 run/validate-report/inspect-doc；__main__ block 含 SystemExit；reconfigure 块含 utf-8 与 AttributeError/OSError；future annotations

### 撞墙记录
- 9 fail（修复）：
  - subparser argument count：未排除 -h/--help action，把 help 也算进 optional → 改为 `a.dest != 'help'` 过滤
  - _format_metric exact format：手写 expected spaces 数错 → 改用 Python f-string `f"  {'foo':36} ..."` 构造
  - elements=None 显式：误以为 `or []` 保护 metrics 计算；实际 `_run_inspect_doc` 把原 doc 传给 compute_automatic_metrics，metrics.py 用 `.get('elements', [])` 拿到 None（key 存在）→ len(None) TypeError → 改为 expect TypeError
  - validate-report OK：构造的报告带了 manifest_version/evaluator_version 顶层 key，schema additionalProperties=false 拒绝 → 移除这两个顶层 key（只保留 report_version）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 224 后）：19625 pass / 0 fail / 15 skip（HEAD `a045fa5`）

### 下一步建议
- 候选 KS：evaluation/runner.py 第十二轮（227 行）
- 候选 KT：evaluation/manifest.py 第十二轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十一轮（194 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和 912 测试/15 行）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和 69 测试/28 行）
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/runner.py 第十二轮）继续推 evaluation 大文件。

---
## Round 225 — evaluation/runner.py 第十二轮（89 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十二轮 edges 测试，覆盖 _load_annotation JSON 标量、_process_one 内部细节、run_evaluation 报告文件格式

### 改动
- 新增 `tests/test_evaluation_runner_edges12.py`（89 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation 深度**：JSON 空 dict / 空 list / null / 标量 int/string/true；两个 JSON 对象相连；纯空白；纯文本；只有 `{`；路径含空格/中文；显式 None 输入；深层嵌套；array values；JSON 后额外内容；末尾换行合法
- **_process_one 深度**：total_seconds 是 float 且非负；image_dir 来自 image_output_dir_for；document=None 时 image_dir=None；error dict 精确 2 keys；unknown error dict 精确 2 keys；out_stub 路径在 _per_doc/<doc_id>.json；parser_name/max_chars/write_json 透传到 process_single
- **run_evaluation 报告文件**：per_doc 公共 4 keys 精确；wall_time_seconds 5 keys 精确；expected_failures 4 keys 精确；文件用 indent=2；ensure_ascii=False（保留中文）；output_path 接受 str/Path；创建父目录；返回 dict 与文件一致；annotation_resolved 三种状态（存在/缺失/None）；aggregate_summary / build_devset_section / build_provenance 调用验证；内部 per_doc_results 含 3 个私有字段；空 documents 不创建 _per_doc 目录
- **模块结构**：13 个 imports（json/time/Path/Any/image_output_dir_for/process_single/REPORT_VERSION/chunk_boundary_prf/figure_caption_prf/compute_automatic_metrics/aggregate_summary/build_devset_section/build_provenance）；__all__==["run_evaluation"]；docstring 含 pipeline/total/not_instrumented；future annotations；3 个 callable
- **签名**：_load_annotation(path)；_process_one(doc, output_root, parser_name, max_chars)；run_evaluation(manifest, output_path, parser_name, max_chars, tolerance_chars) - 后 3 个 keyword-only，默认 fallback/800/30
- **综合**：两 doc 完整流程；doc + expected_failure 共存；首个 parser_version 进 provenance；报告含 unicode doc_id

### 撞墙记录
- 1 fail（修复）：test_run_evaluation_idempotent_report_file 误以为两次 run 内容完全一致；实际 run_timestamp_iso + wall_time.total 每次不同 → 改为只验证结构一致 + ts1≠ts2

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 225 后）：19714 pass / 0 fail / 15 skip（HEAD `b24d737`）

### 下一步建议
- 候选 KT：evaluation/manifest.py 第十二轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十一轮（194 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT（evaluation/manifest.py 第十二轮）继续推 evaluation 大文件。

---
## Round 226 — evaluation/manifest.py 第十二轮（122 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十二轮 edges 测试，覆盖 _is_absolute_like/_has_backslash 边界、_resolve_relative_path 错误消息、load_manifest str/Path 输入、Manifest properties

### 改动
- 新增 `tests/test_evaluation_manifest_edges12.py`（122 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like 深度**：bytes/None/int 输入行为；digit/underscore/dot/dash 不是字母；3-char 边界（含 separator 与不含）；lowercase/uppercase alpha；double slash network path（False）；Unicode alpha drive；返回 bool；相对路径/纯文件名/./.gitignore/../foo 都是 False
- **_has_backslash 深度**：bytes/None 输入 TypeError；empty/only backslash/at start/middle/end/multiple/forward slash only/mixed 都正确判定；返回 bool
- **_resolve_relative_path 深度**：field_name 出现在 4 种错误消息中（empty/absolute/backslash/outside_root）；返回 Path 对象；resolved 是 absolute；result 在 project_root 内；subdirectory parent 链；explicit ./ 前缀；double slash 折叠；返回 existing file 的 is_file() True；project_root 是 file 时 Path 拼接按 component 工作（不抛错）
- **load_manifest 深度**：str/Path 双向接受（manifest_path & project_root 都测）；missing file/directory/invalid JSON/empty file 都抛 ManifestError；empty documents/expected_failures 都返回空 tuple；docs + efs 共存；6 个 round-trip（resolved_path/path_str/source_type/categories/paired_with/sha256/annotation_file/expectations）；expected_failure 含/不含 source_type
- **Manifest properties 深度**：source_type='unknown' 既不算 pdf 也不算 docx；pdf+docx+unknown 混合；categories_covered 每次 new list；case sensitive 排序；空 docs/categories；file_count == len(documents)；5 个 properties 都是 property（不需调用）
- **dataclass frozen**：Manifest/DocumentEntry/ExpectedFailure 都触发 FrozenInstanceError；replace() 保留其他字段
- **_detect_project_root 深度**：返回 Path 对象；is_absolute；只有 .git 不识别（只看 pyproject.toml）；多层目录中找最近；signature (start,)
- **模块结构**：6 个 imports；__all__ exact 5 个名字；__all__ 不含 internal helpers；docstring 提及 invariants；future annotations；ManifestError 是 Exception 子类、不是 RuntimeError 子类；ManifestError init 多种 args 形式
- **签名**：load_manifest(manifest_path, project_root=None)；_is_absolute_like(path_str)；_has_backslash(path_str)；_resolve_relative_path(path_str, project_root, field_name) - field_name 无默认
- **综合**：完整 round-trip（2 docs + 2 efs + annotation + expectations + paired_with + sha256 + categories）；3 个 dataclass 字段数（DocumentEntry=10, ExpectedFailure=5, Manifest=5）

### 撞墙记录
- 14 fail（修复）：
  - `_is_absolute_like(None)`：误以为抛 TypeError；实际 `if not path_str: return False` 命中（None falsy）→ 改为 expect False
  - `_is_absolute_like(123)`：误以为抛 TypeError；实际 int 没有 .startswith → AttributeError
  - `_resolve_relative_path_subdirectory`：parent 链数错（sub/dir/foo.txt 的 parent.parent.parent 才是 root）
  - `_resolve_relative_path_project_root_can_be_file_parent`：误以为抛 ManifestError；实际 Path 拼接按 component 工作（marker.txt/sub.txt.relative_to(marker.txt) = sub.txt 成功）→ 改为 expect 不抛错
  - 10 个 load_manifest round-trip 用 source_type='text'（schema enum 只允许 pdf/docx）→ 改为 'pdf'/'docx'；sha256 "x" * 64 是 x 不是 hex → 改为 "a" * 64

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 226 后）：19836 pass / 0 fail / 15 skip（HEAD `8f9b778`）

### 下一步建议
- 候选 KE：evaluation/annotation_metrics.py 第十一轮（194 行）
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE（evaluation/annotation_metrics.py 第十一轮）继续推 evaluation 大文件。

---
## Round 227 — evaluation/annotation_metrics.py 第十一轮（89 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十一轮 edges 测试，覆盖 PARSER_DOES_NOT_EMIT_RELATIONS 常量、figure_caption_prf 输入不变性、chunk_boundary_prf 输入类型边界

### 改动
- 新增 `tests/test_annotation_metrics_edges11.py`（89 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **PARSER_DOES_NOT_EMIT_RELATIONS 常量**：是 str；值精确 == "parser_does_not_emit_relations"；非空；在 __all__ 中
- **figure_caption_prf 深度**：返回 dict[str, dict]；keys 精确 3 个；所有输入组合（None/{} /present）都返回 null + reason；不依赖 annotation/document 内容；callable；signature；param kinds；no defaults
- **chunk_boundary_prf 输入类型边界**：document 是 list/str → AttributeError（提供 annotation 触发 document 访问）；annotation 是 list（非空）→ AttributeError；annotation 是空 list → 走 no_annotation 路径；chunks 含 None/str/int 元素 → AttributeError；chunk text 是 int/dict/list → TypeError（normalize_text regex 期望 str）；chunk_boundary_anchors 是 dict/int → AttributeError/TypeError；anchor marker 是 int → TypeError（stream.find 期望 str）；anchor position 是 int/None → 走 else (after) 分支；tolerance_chars 是 str → TypeError
- **chunk_boundary_prf 算法精确性**：tolerance=0/negative/very large 行为；predicted boundary 在 chunk 末尾；position before/after；last chunk 不贡献边界（N-1）；whitespace/newline/multi-space normalize；marker 含 regex 元字符（按字面匹配）；marker unicode；repeated markers 推进 search_from；missing marker 记入 _missing_markers；all found 时无 _missing_markers key
- **chunk_boundary_prf _null 路径精确性**：doc=None → pipeline_failed；annotation=None/空 dict → no_annotation；0/1 chunks → no_predicted_boundaries；chunks present no anchors → no_ground_truth_anchors；anchor 缺 marker → 默认 "" → missing；anchor 缺 position → 默认 after；position unknown → after 分支
- **chunk_boundary_prf 内部 vs 外部 keys**：_tolerance_chars / _missing_markers 以 _ 开头；precision/recall/f1 不以 _ 开头；无 side effects
- **模块结构**：__all__ exact 3 个；imports Counter/Any/normalize_text/_null/_ratio；docstring 含 chunk_boundary/figure_caption/一对一/tolerance；future annotations；常量计数
- **签名**：chunk_boundary_prf(document, annotation, tolerance_chars=30) 全部 positional-or-keyword；figure_caption_prf(document, annotation) 无默认
- **综合**：full perfect match（3 chunks + 2 anchors）；half match（5 chunks + 2 anchors → 2 matches in tolerance）；一对一约束（1 predicted + 2 anchors in tolerance → only 1 match）

### 撞墙记录
- 6 fail（修复）：
  - document 是 list/str：annotation=None 触发 early return，从未访问 document.get → 改为提供非空 annotation 触发访问
  - chunk text 是 int/dict/list：误以为 AttributeError；实际 normalize_text 调用 regex.sub 触发 TypeError → 改为 expect TypeError
  - one_to_one_constraint：用 marker='abc' 的两个 anchor，search_from 推进导致第二个找不到（missing），实际只 1 anchor 进入 gt_positions；改用 'b' 和 'c' 两个不同 marker 让两个 anchor 都找到

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 227 后）：19925 pass / 0 fail / 15 skip（HEAD `d77ce5c`）

### 下一步建议
- 候选 KZ：evaluation/schema.py 第六轮（80 行）
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和）
- 候选 KF/KW：base.py / chunkers/base.py / hash_util.py（仍饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ（evaluation/schema.py 第六轮）补 evaluation 中等大小文件。

---
## Round 228 — evaluation/schema.py 第六轮（87 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第六轮 edges 测试，覆盖 EvalSchemaError 错误类型、_schema_path 边界、load_schema 可变性、validate/validate_file 错误优先级

### 改动
- 新增 `tests/test_evaluation_schema_edges6.py`（87 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **EvalSchemaError 深度**：errors 是 tuple/dict/int 输入（truthy 保留原值，falsy → []）；init 接 kwargs；可子类化；str/repr 含 unicode/换行；args 含 message；init 后可写 errors 属性
- **_schema_path 深度**：空 name（raises 因为 SCHEMAS_DIR/'' 是 dir）；subdir name；dot prefix；返回路径在 SCHEMAS_DIR 下
- **load_schema 深度**：每个已知 schema 返回可变独立 dict；未知 name raises FileNotFoundError；callable；signature
- **validate 深度**：instance 类型 list/str/int/None 都 raise EvalSchemaError；空 dict raises；errors 按 path 排序；head message 含首错；callable；signature；无默认值；不修改 instance
- **validate_file 深度**：BOM 文件 raises JSONDecodeError；trailing comma/single quotes raise；array/int/str/null/bool root JSON 全 raise EvalSchemaError；空文件 raises；优先级（FileNotFoundError > JSONDecodeError > Schema）；成功返回 None；接受 str/Path；目录 raises
- **模块结构**：__all__ 精确 5 个；imports json/Path/Any/Draft202012Validator/JSValidationError；docstring 提到 schema/与 app 分离；SCHEMAS_DIR 是 Path/absolute/exists；EvalSchemaError 是 Exception 子类带 docstring；_schema_path internal（不在 __all__）
- **综合**：validate 后 load_schema round-trip；EvalSchemaError 链式 __cause__；try/except/finally raise 传播；复杂嵌套错误路径（documents/0/source_type）；多余 top keys 拒绝；SCHEMAS_DIR 解析（无 .. 或 .）

### 撞墙记录
- 0 fail（首次跑过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 228 后）：20012 pass / 0 fail / 15 skip（HEAD `e095241`）

### 下一步建议
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KAA：evaluation/schema_validation.py 第四轮（15 行 — 已饱和）
- 候选 KAB：evaluation/__init__.py 第二轮（28 行 — 已饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW（evaluation/report.py 第十二轮）继续推 evaluation 大文件。

---
## Round 229 — evaluation/metrics.py 第十一轮（116 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十一轮 edges 测试，覆盖模块常量精确内容、_chunk_reference_ratio None 边界、_heading_boundary_ratio first id None、_text_preservation 全 image / 非 str content、_image_resource_ratio 绝对路径、_docx_locator_ratio 7 个 structural key、_pdf_locator_ratio type 不在 BBOX_REQUIRED、_silent_drop_count 多 type 求和、compute_automatic_metrics metric name 集合

### 改动
- 新增 `tests/test_evaluation_metrics_edges11.py`（116 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块常量精确内容**：_TEXT_TYPES 7 项（heading/paragraph/list_item/table/caption/header/footer）；_PDF_BBOX_REQUIRED_TYPES 4 项（heading/paragraph/caption/list_item）；_NOT_EVALUATED = "not_evaluated"；都是 tuple；不在 __all__
- **_chunk_reference_ratio**：elements 含 None element_id（set 含 None）；chunks first id None；duplicate id 在 chunk 内（all() 仍 True）；duplicate element_id 在 elements 内（set 去重）；half valid 比例精确
- **_heading_boundary_ratio**：chunk first id None 加入 set；heading element_id None 匹配；multiple chunks 同 first id（set 去重）；multiple headings 部分匹配（2/3）
- **_text_preservation**：全 image type → expected=""；content None → or "" → ""；content int/list → TypeError；text int → TypeError；precision/recall 算法精确（Counter 交集）；dup char in actual/expected
- **_image_resource_ratio**：image_base_dir 是文件（仍 work）；resource_path 是绝对路径存在/缺失；resource_path 是目录；resource_path="" → falsy；0 字节文件 invalid
- **_docx_locator_ratio**：7 个 structural key 全在一个 element；relationship_id/section 单独足够；page/bbox 出现 → invalid；unknown key → invalid；empty locator → invalid
- **_pdf_locator_ratio**：type=None 不在 BBOX_REQUIRED；type=image/table/header/footer 只需 page≥1；type=paragraph/caption/list_item 需 page + bbox；page=0/negative/string/float/bool 边界
- **_silent_drop_count**：expectations 含未知 key 被忽略；actual 含 expectations 没有的 type 不算；多 type 求和精确；negative expected 不算 drop；zero expected zero actual = 0；value 类型 int
- **compute_automatic_metrics**：metric name 集合精确（14 keys 成功 / 14 keys 失败）；不含 chunk_boundary_*/figure_caption_*（那些来自 annotation_metrics）；source_type='pdf'/'docx'/'other' locator null 切换；error_code 缺 code 字段 raises KeyError；schema_check_exception path 返回 False + reason 含异常类型名
- **_strip_unicode_whitespace**：\f (form feed) 删除；\v (vertical tab) 删除；\r 删除；\x00 (null) 保留；\x07 (BEL) 保留；\x1b (ESC) 保留
- **_is_valid_bbox**：tuple/set/dict 全 reject；complex number 元素 reject；str 元素 reject；None 元素 reject；4 个 0.0 valid；负坐标 valid；4 个最小正 float valid

### 撞墙记录
- 1 fail（修复）：
  - test_compute_metrics_failure_path_metric_count：误以为失败路径 13 keys；实际是 14 keys（pipeline_success + error_code + schema_valid + 11 null）→ 改为 expect 14

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 229 后）：20128 pass / 0 fail / 15 skip（HEAD `4b7f2e6`）

### 下一步建议
- 候选 KW：evaluation/report.py 第十二轮（200 行）
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW（evaluation/report.py 第十二轮）继续推 evaluation 大文件。

---
## Round 230 — evaluation/report.py 第十二轮（79 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十二轮 edges 测试，覆盖 _RATIO_METRICS/_COUNT_METRICS/_SUCCESS_BOOL_METRICS 精确元组等值、三组互斥、各公共函数返回 dict 的插入顺序、aggregate_summary value 类型在算术中的行为

### 改动
- 新增 `tests/test_evaluation_report_edges12.py`（79 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量元组精确等值**：_RATIO_METRICS 12 项按精确顺序（schema_valid 排第一、chunk_boundary_f1 排最后、chunk_boundary 三项连续、text_char_multiset 两项连续）；_COUNT_METRICS = ("element_count_total",)；_SUCCESS_BOOL_METRICS = ("pipeline_success",)；三组 pairwise 互斥
- **get_git_provenance**：返回 dict 按 git_commit → git_dirty 顺序；精确 2 keys 无 extra；subprocess.run 必须以 cwd=str(project_root) / encoding='utf-8' / errors='replace' / capture_output=True / text=True 调用
- **get_dependency_versions**：返回 dict 按 pdfplumber → python-docx → pypdfium2 顺序；精确 3 keys
- **build_provenance**：返回 dict 按 9 个 key 顺序（git_commit/git_dirty/evaluator_version/report_version/parser_name/parser_version/dependencies/max_chars/run_timestamp_iso）；empty parser_name/parser_version 原样保留；None parser_version 原样保留；max_chars=0/negative 原样保留；run_timestamp_iso 能被 fromisoformat 解析；evaluator_version/report_version 来自 evaluation 模块常量
- **build_devset_section**：返回 dict 按 6 个 key 顺序（status/file_count/content_group_count/pdf_count/docx_count/categories_covered）；zero/negative counts 透传；categories 可以是 dict
- **aggregate_summary top-level**：返回 dict 按 4 个 key 顺序（counts/success_rates/ratio_macro_averages/silent_drop_total）；counts section 1 entry；success_rates section 1 entry；ratio_macro_averages section 12 entries
- **aggregate_summary value 类型行为**：ratio value=True → 算术中等于 1；ratio value=int/float → 参与 macro；ratio value=0.0（falsy 但 not None）→ 参与；count value=True → sum 中等于 1；count value=False → sum 中等于 0；silent_drop_count value=True → sum 中等于 1；pipeline_success value=1（int）/ 1.0（float）→ is True False → 不计入 success_count
- **aggregate_summary entry keys**：counts entry 2 keys (sum, participating_docs)；success_rates entry 3 keys (success_count, total, rate)；ratio_macro_averages entry 3 keys (macro_average, participating_docs, not_evaluated)
- **aggregate_summary not_evaluated**：not_evaluated = total - participating_docs；all participate → 0；none participate → total
- **module-level 结构**：imports subprocess/datetime/Path/Any/EVALUATOR_VERSION/REPORT_VERSION；__all__ 精确 5 项（不含私有常量）；future annotations；docstring 提到聚合规则
- **综合**：1 doc 全 metrics set / 2 docs mixed metrics；figure_caption_* 不在 _RATIO_METRICS 中（aggregate 不处理）

### 撞墙记录
- 0 fail（首次跑过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 230 后）：20207 pass / 0 fail / 15 skip（HEAD `d6de4ff`）

### 下一步建议
- 候选 KX：evaluation/cli.py 第十三轮（243 行）
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX（evaluation/cli.py 第十三轮）继续推 evaluation 大文件。

---
## Round 231 — evaluation/cli.py 第十三轮（80 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十三轮 edges 测试，覆盖 _format_metric 非 dict metric 输入、name 边界、reason 非 str、Counter 类型；_run_inspect_doc source_type 默认/elements/chunks None 传播 TypeError；main 各子命令目录/不存在路径；module subparser 结构

### 改动
- 新增 `tests/test_evaluation_cli_edges13.py`（80 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_format_metric 非 dict metric**：metric=None/int/list/str/tuple/set → 全部 AttributeError（None 没有 .get）
- **_format_metric name 边界**：name='' 仍能渲染；name 恰好 36 字符不补 padding；name > 36 字符不截断；name 含 unicode/特殊字符原样渲染；name=None raises TypeError；name=int 自动转 str
- **_format_metric reason 非 str**：reason=int(42)→渲染 '42'；reason=0→falsy→'ok'；reason=''→'ok'；reason=['x']→truthy 渲染 str；reason=None + value=None → '(None)'（无 fallback）；reason=0 + value=None → '(0)'
- **_format_metric value 类型**：Counter（dict 子类）走 dict 分支；dict 含 int keys sorted 按 int；dict 含 tuple keys 仍能 sort；dict 含 mixed key types raises TypeError；float 0.00001 → '0.0000'；float 1234567.89 → '1234567.8900'；float -0.5 → '-0.5000'；pi → '3.1416'
- **_run_inspect_doc**：source_type 默认 'unknown'；source_type 显式 'pdf'；elements=None 显式触发 TypeError（compute_automatic_metrics 的 .get 在 key 存在时返回 None，len(None) 失败）；chunks=None 同；tolerance_chars=0/negative/large 都 work；不写盘；stdout 含 'metrics:' / 'file:' / 'document_id:' / 'parser:' header；缺 document_id → '?'
- **main 路径边界**：validate-report/inspect-doc/run input 是目录 → return 2；input 不存在 → return 2
- **main argparse**：run 缺 --manifest/--output → SystemExit 2；validate-report/inspect-doc 缺 input → SystemExit 2；无 command → SystemExit 2；prog = 'evaluation.cli'；subparser required=True；dest='command'；3 子命令集合精确
- **_format_metric 综合行为**：int value=1/0/-5/large → 默认分支；unicode/long string 原样渲染；返回 str 类型；非空；以 '  ' 开头；dict value empty/items/None/bool/negative
- **module 结构**：description 含 '评测'；_choices_actions 3 个；run/validate-report/inspect-doc 子 parser prog 含自身名

### 撞墙记录
- 6 fail（修复）：
  - elements=None / chunks=None 显式：误以为 _run_inspect_doc 局部 normalize 后 metrics 也用 normalized；实际 metrics 接收原始 doc，.get('elements', []) 返回 None → len(None) TypeError → 改为 expect TypeError
  - module_description_contains_subcommands：description 不含 'run' 字面；改为检查 _choices_actions 长度
  - run_p/val_p/ins_p.help：ArgumentParser 没有 .help 属性（help 是 subparser action 的属性，不是子 parser 自身）；改为检查 prog 含子命令名

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 231 后）：20287 pass / 0 fail / 15 skip（HEAD `def2d34`）

### 下一步建议
- 候选 KS：evaluation/runner.py 第十三轮（227 行）
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 候选 KW：evaluation/report.py 第十三轮（200 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/runner.py 第十三轮）继续推 evaluation 大文件。

---
## Round 232 — evaluation/runner.py 第十三轮（45 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十三轮 edges 测试，覆盖 report top-level dict 插入顺序、per_doc entry / wall_time_seconds / expected_failure entry 插入顺序、_per_doc 目录在 run 后仍存在、_process_one out_stub 清理、parser_version_for_prov 行为

### 改动
- 新增 `tests/test_evaluation_runner_edges13.py`（45 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **report top-level insertion order**：6 个 key 按 report_version → provenance → devset → summary → per_doc → expected_failures 顺序
- **per_doc entry insertion order**：4 个 key 按 doc_id → source_type → metrics → wall_time_seconds 顺序
- **wall_time_seconds insertion order**：5 个 key 按 total → parse → chunk → parse_reason → chunk_reason 顺序；parse/chunk 固定 None；reason 固定 'not_instrumented'；total 是 float
- **expected_failure entry insertion order**：4 个 key 按 doc_id → expected_error_code → actual_error_code → matches 顺序
- **_per_doc directory**：run 之后 _per_doc 目录仍存在；目录内 .json 文件全清理；多 docs 也只有一个 _per_doc 目录
- **output_root**：缺失时被创建；已存在时不抛异常
- **parser_version_for_prov**：first non-None wins；all docs fail → None；first None + second 有值 → second wins
- **_process_one**：out_stub 在 success 路径被 unlink；out_stub 不存在时不抛；elapsed >= 0；parser_version on success/failure；image_dir is None when document is None；image_dir is Path when document present；document None + no errors → 'unknown' error code
- **report file**：valid JSON；indent=2（行以 2 space 开头）；ensure_ascii=False（中文不转义）；返回 dict 与写盘内容一致
- **annotation_resolved**：None → figure_caption null；文件不存在 → null；文件存在（空 dict） → null
- **tolerance_chars 透传**：显式值（42）/ 默认值（30）都到达 chunk_boundary_prf
- **max_chars / parser_name 透传**：都到达 process_single
- **write_json=False**：_process_one 调用 process_single 时永远 write_json=False
- **devset 透传**：status / file_count / categories_covered 都从 manifest 透传到 report

### 撞墙记录
- 2 fail（修复）：
  - tolerance_chars_passed_to_chunk_boundary_prf：误以为 monkeypatch 'evaluation.annotation_metrics.chunk_boundary_prf' 能拦截；实际 runner.py 用 `from evaluation.annotation_metrics import chunk_boundary_prf` 把名字导入本地命名空间，需要 patch 'evaluation.runner.chunk_boundary_prf'

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 232 后）：20332 pass / 0 fail / 15 skip（HEAD `4727a08`）

### 下一步建议
- 候选 KT：evaluation/manifest.py 第十三轮（239 行）
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 候选 KW：evaluation/report.py 第十三轮（200 行）
- 候选 KX：evaluation/cli.py 第十四轮（243 行）
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT（evaluation/manifest.py 第十三轮）继续推 evaluation 大文件。

---
## Round 233 — evaluation/manifest.py 第十三轮（94 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十三轮 edges 测试，覆盖 _is_absolute_like/_has_backslash/_resolve_relative_path 深度边界、Manifest dataclass 字段精确、properties 返回类型、content_group_count 自环/链/环/双向、categories_covered 大小写敏感、ManifestError docstring、load_manifest expectations/annotation_file/paired_with/categories/sha256 透传

### 改动
- 新增 `tests/test_evaluation_manifest_edges13.py`（94 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like**：3 字符 alpha+slash / drive+colon；4 字符 drive+path；纯字母；纯数字；字符串第 [0]/[1]/[2] 位
- **_has_backslash**：mixed slash（forward + back）；纯 forward 不算
- **_resolve_relative_path**：path_str 同时含正反斜杠；多层 subdir；trailing slash；dot/dotdot 混合
- **DocumentEntry dataclass fields()**：字段名/类型/默认值精确
- **ExpectedFailure dataclass fields()**：字段名/类型精确
- **Manifest dataclass fields()**：6 个字段名精确
- **Manifest properties**：返回类型（int/list/tuple/Path/Optional[Path]）；每次调用返回新对象
- **content_group_count**：self-pair（自己跟自己一组）；pair 到不存在的 doc_id；链式 A-B-C；环 A-B-C-A；双向 A↔B（去重）
- **categories_covered**：case-sensitive sort（"PDF" ≠ "pdf"）；unicode 排序
- **ManifestError**：docstring 非空；是 Exception 子类
- **load_manifest**：expectations 含 element_count_by_type / required_markers 透传；annotation_file None；paired_with 透传；categories 透传；sha256 透传；doc_id 重复触发 ManifestError
- **module __all__**：导出顺序精确

### 撞墙记录
- 1 fail（修复）：
  - test_load_manifest_expectations_none：以为 schema 允许 expectations: null 走到 `d.get("expectations")`；实际 manifest.schema.json 定义 expectations 为 `{"type": "object", "additionalProperties": false, ...}` 不允许 null，schema 验证先抛 EvalSchemaError → 改成 expect EvalSchemaError 并加注释说明

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 233 后）：20426 pass / 0 fail / 15 skip（HEAD `5e3155f`）

### 下一步建议
- 候选 KE：evaluation/annotation_metrics.py 第十二轮（194 行）
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 候选 KW：evaluation/report.py 第十三轮（200 行）
- 候选 KX：evaluation/cli.py 第十四轮（243 行）
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE（evaluation/annotation_metrics.py 第十二轮）继续推 evaluation 大文件。

---
## Round 234 — evaluation/annotation_metrics.py 第十二轮（81 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十二轮 edges 测试，覆盖 anchor 元素类型、chunks/anchors None 表现为空、各分支 dict 插入顺序、_missing_markers 结构、空 marker、空 chunk、tolerance_chars 浮点、module __all__ 顺序、函数 docstring 关键词、f1 各路径、签名精确

### 改动
- 新增 `tests/test_annotation_metrics_edges12.py`（81 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **anchor 元素类型**：anchor 是 None/str/int/list/tuple/set 触发 AttributeError；anchor list 第 2 个 None 也抛
- **chunks/chunk_boundary_anchors = None**：通过 `or []` 走空 list 分支
- **dict 插入顺序精确**：doc=None/annotation 空/0 chunks/无 anchors/成功无 missing/成功有 missing 共 6 个分支验证 keys 顺序
- **figure_caption_prf dict 插入顺序**：3 keys 顺序
- **_missing_markers**：value 是 list；reason 永远 None；多 missing 顺序保留；全 missing 时 recall null
- **空 marker**：空字符串 + before/after 都进 missing；空 dict anchor → marker="" → missing
- **predicted boundaries 数量**：2 chunks→1, 3 chunks→2, 4 chunks→3
- **空 chunk**：第 1 个 chunk 空 → predicted boundary at 0；中间 chunk 空 → predicted boundary at prev end
- **tolerance_chars**：浮点保留；0 边界不匹配距离 1；1 边界匹配距离 1；所有路径都透传
- **module __all__**：顺序精确（PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf）
- **module 命名空间**：Counter/_null/_ratio/normalize_text/Any 都在
- **函数 docstring**：figure_caption_prf 含 null/caption；chunk_boundary_prf 含 normalize/tolerance/precision/recall/anchor/Args
- **f1 路径**：完全匹配 1.0；半匹配公式；零匹配 denom=0 → 0.0；recall null → f1 null(precision_or_recall_not_evaluated)
- **一对一约束**：两 anchor 同 marker → 第 2 个 missing；2 predicted + 1 anchor → precision=0.5
- **签名**：3 参数 + 默认值；2 参数 figure_caption_prf 无默认值

### 撞墙记录
- 1 fail（修复）：
  - test_figure_caption_prf_docstring_mentions_caption：以为 docstring 含英文 "caption"；实际是中文 "图表关联" → 改成接受中文 "关联" 或英文 "caption"

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 234 后）：20507 pass / 0 fail / 15 skip（HEAD `fa8f31f`）

### 下一步建议
- 候选 KF：evaluation/metrics.py 第十二轮（381 行）
- 候选 KW：evaluation/report.py 第十三轮（200 行）
- 候选 KX：evaluation/cli.py 第十四轮（243 行）
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF（evaluation/metrics.py 第十二轮）继续推 evaluation 最大文件。

---
## Round 235 — evaluation/metrics.py 第十二轮（119 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十二轮 edges 测试，覆盖 compute_automatic_metrics dict 插入顺序、_text_preservation 返回顺序、各 helper 类型边界、_is_valid_bbox 各种类型、_strip_unicode_whitespace 特殊空白、document={} 空字典路径

### 改动
- 新增 `tests/test_evaluation_metrics_edges12.py`（119 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **compute_automatic_metrics 输出 dict 插入顺序**：success / failure 两路都验证 14 keys 顺序精确
- **_text_preservation 返回 dict 顺序**：equal, precision, recall
- **_chunk_reference_ratio**：source_element_ids 是 str → 字符迭代；是 int → TypeError；0/''/None → falsy 当空
- **_heading_boundary_ratio**：source_element_ids 是 str → 字符首字符加入；int → TypeError；falsy → 跳过
- **_pdf_locator_ratio / _docx_locator_ratio**：elements=[{}] 缺 source_locator → loc={} → invalid
- **_pdf_locator_ratio**：header/footer/table/image 类型只需 page≥1（不在 _PDF_BBOX_REQUIRED_TYPES）
- **_docx_locator_ratio**：paragraph_index / section / table_index+row+col 单独足够
- **_image_resource_ratio**：image 缺 resource_path / None / '' / 0 都当 falsy
- **_silent_drop_count**：expectations={} / None / 无 element_count_by_type / None 值都返回 null reason；string expected 触发 TypeError
- **_is_valid_bbox**：内嵌 list/dict/complex/3-5 元素/极大 finite 都正确判定
- **_strip_unicode_whitespace**：NBSP/EM/EN/ideographic/line/paragraph separator 都识别为 whitespace；ZWJ 不是 whitespace；emoji 保留
- **_null/_ratio/_bool_metric/_int_metric**：每次返回新 dict；keys 精确；value 类型精确
- **compute_automatic_metrics**：document={} 走通空字典路径；source_type 未知 → 两 locator 都 not_pdf/not_docx
- **_text_preservation**：image 排除；chunk text None/缺键当空；element content None/缺键当空；Counter 交集 min 语义；超集 precision<1
- **module __all__**：1 个元素；内部 helper 不导出但可访问

### 撞墙记录
- 0 fail：119 测试一次性通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 235 后）：20626 pass / 0 fail / 15 skip（HEAD `555b504`）

### 下一步建议
- 候选 KW：evaluation/report.py 第十三轮（200 行）
- 候选 KX：evaluation/cli.py 第十四轮（243 行）
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW（evaluation/report.py 第十三轮）继续推 evaluation 中型文件。

---
## Round 236 — evaluation/report.py 第十三轮（95 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十三轮 edges 测试，覆盖 module 常量精确、aggregate_summary 空 list/success_rate/silent_drop/macro_average、build_provenance 类型边界、build_devset_section 各种值、get_git_provenance subprocess 命令精确、函数签名、__all__ 顺序

### 改动
- 新增 `tests/test_evaluation_report_edges13.py`（95 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **常量精确**：_RATIO_METRICS=12, _COUNT_METRICS=1, _SUCCESS_BOOL_METRICS=1；不互相包含；不含 figure_caption_/_/error_code
- **aggregate_summary 空 list**：4 top keys；counts element_count_total.sum=None；success_rate rate=None；ratio_macro 全 None；silent_drop_total=None
- **success_rate**：全 success / 全 fail / 半 / value=None / metric 缺失
- **silent_drop_total**：全有 / 一 None / 全 0 / 负值 / 缺失 key
- **ratio_macro_averages 12 keys 顺序**：精确
- **macro_average**：半参与 / 0.0 参与 / 全参与
- **build_provenance**：max_chars bool/float/string(ValueError)；parser_name None/int；parser_version int/empty/unicode；EVALUATOR/REPORT_VERSION 常量；run_timestamp_iso 可解析
- **build_devset_section**：0/负值/tuple/set categories；missing property AttributeError
- **get_git_provenance**：subprocess 命令精确（rev-parse HEAD + status --porcelain）；commit strip；dirty 检测；returncode!=0 / OSError / SubprocessError fallback；timeout=10；cwd=str
- **get_dependency_versions**：3 keys；str-or-None；idempotent
- **签名精确**：5 个函数的参数数量与名字
- **__all__ 顺序**：5 个元素

### 撞墙记录
- 0 fail：95 测试一次性通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 236 后）：20721 pass / 0 fail / 15 skip（HEAD `2fbd419`）

### 下一步建议
- 候选 KX：evaluation/cli.py 第十四轮（243 行）
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX（evaluation/cli.py 第十四轮）继续推 evaluation 大文件。

---
## Round 237 — evaluation/cli.py 第十四轮（90 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十四轮 edges 测试，覆盖模块 imports 精确、_format_metric 精度边界与 value/reason 组合、argparse 错误路径、_run_inspect_doc 顶层非 dict、_build_parser 详细结构

### 改动
- 新增 `tests/test_evaluation_cli_edges14.py`（90 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块 imports**：argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file 都在命名空间
- **模块结构**：无 __all__；__name__ guard 调用 SystemExit(main())；有 sys.stdout.reconfigure 块
- **_format_metric 精度**：0.5→0.5000；0.12345→0.1235（rounds）；0.12344→0.1234；0.99995→1.0000；-0.0→-0.0000；pi→3.1416；e→2.7183
- **_format_metric 组合**：empty dict → null(None)；None+None；None+custom；True+None→(ok)；True+empty→(ok)；True+custom；False+None；False+custom；0 int + empty→(ok)；-5+0→(ok)
- **列宽 36**：short name padding；36 chars no padding；37 chars 不截断
- **argparse 错误**：unknown command SystemExit(2)；--help SystemExit(0)；run/validate/inspect --help 都 0；invalid parser choice；non-int max-chars/tolerance-chars；missing required/positional
- **_run_inspect_doc 返回 int**：0 成功；1 bad JSON / array / string / int 顶层；2 missing file
- **main 返回 int**：validate-report missing file → 2；inspect-doc missing → 2；run missing manifest → 2
- **_build_parser 详细**：ArgumentParser 实例；SubParsersAction；3 choices；run 5 args / validate 1 / inspect 2；--parser default=fallback；--max-chars 800；--tolerance-chars 30；type=int；choices 精确
- **formatter_class RawDescriptionHelpFormatter**；prog evaluation.cli
- **sort order**：bool 第一行/null 最后一行；_tolerance_chars 在输出中
- **callable 验证**：4 个 module-level function

### 撞墙记录
- 0 fail：90 测试一次性通过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 237 后）：20811 pass / 0 fail / 15 skip（HEAD `8bf0951`）

### 下一步建议
- 候选 KS：evaluation/runner.py 第十四轮（227 行）
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS（evaluation/runner.py 第十四轮）继续推 evaluation 中型文件。

---
## Round 238 — evaluation/runner.py 第十四轮（73 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十四轮 edges 测试，覆盖 module imports、__all__、_load_annotation 函数、_process_one 返回 tuple 类型、空 manifest 行为、provenance/devset/summary 结构、函数签名

### 改动
- 新增 `tests/test_evaluation_runner_edges14.py`（73 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **module imports**：13 个导入名字都在命名空间
- **__all__**：1 个元素（run_evaluation）；私有 helper 不导出但可访问
- **_load_annotation**：path=None / 缺文件 / JSON 无效 / array / empty / 目录 / utf-8 中文 / 不修改输入
- **_process_one 返回 tuple**：5 元素类型精确（dict|None, dict|None, float, str|None, Path|None）
- **_process_one error shape**：errors[0].to_dict() 透传；document=None+no errors → 'unknown' code；success 返回 parser_version
- **_process_one 副作用**：创建 _per_doc 目录
- **run_evaluation 空 manifest**：6 top keys；per_doc=[]；expected_failures=[]；创建 report 文件；创建 output_root
- **report_version**：与 REPORT_VERSION 常量一致；写盘文件中也是
- **写盘格式**：合法 JSON；indent=2（行以 2 空格开头）
- **provenance/devset/summary**：都是 dict；summary 4 top keys
- **devset 透传**：status/zero counts/categories 都透传
- **provenance 透传**：parser_name/max_chars；空 manifest → parser_version=None
- **default args**：parser_name=fallback；max_chars=800
- **空 manifest 不创建 _per_doc**（_process_one 不被调用）
- **返回 dict 与写盘内容一致**
- **签名**：run_evaluation 5 参数（前 2 positional，后 3 keyword-only）；_process_one 4 参数；_load_annotation 1 参数

### 撞墙记录
- 1 fail（修复）：
  - test_run_evaluation_creates_per_doc_directory：误以为空 manifest 也会创建 _per_doc；实际只有 _process_one 被调用才创建 → 改成验证空 manifest 不创建 _per_doc

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 238 后）：20884 pass / 0 fail / 15 skip（HEAD `128c1c1`）

### 下一步建议
- 候选 KZ：evaluation/schema.py 第七轮（80 行）
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ（evaluation/schema.py 第七轮）继续推 evaluation 最小文件。

---
## Round 239 — evaluation/schema.py 第七轮（77 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第七轮 edges 测试，覆盖 schema 文件清单、各 schema 结构、EvalSchemaError message 格式、validate({}) 各 schema、有效 manifest 校验、_schema_path/load_schema 行为

### 改动
- 新增 `tests/test_evaluation_schema_edges7.py`（77 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **schemas/ 文件清单**：4 个 schema 文件存在；至少 4 个 *.schema.json；目录内只有 .json
- **各 schema 结构**：$schema/type=object/properties 都在；4 个 schema 都是合法 Draft 2020-12
- **EvalSchemaError message 格式**：含 schema_name / '处' / 'path='
- **EvalSchemaError errors 结构**：每项 path/message/schema_path 3 key；都是 list/str 类型
- **validate({})**：manifest/annotation/evaluation-report 都拒绝
- **validate 有效 manifest**：minimal / 1 document / 1 expected_failure 通过
- **validate extra keys**：additionalProperties=false 拒绝
- **_schema_path**：返回 Path 在 SCHEMAS_DIR 内；绝对路径；可 open；missing → FileNotFoundError 含 name 和 'schemas'
- **load_schema**：返回 dict 含 $schema/type；每次新 dict；修改不影响下次
- **validate_file**：含中文 JSON OK；utf-8 编码；str 路径 OK；成功返回 None
- **validate 不修改 instance**
- **EvalSchemaError**：errors 默认 []；mutable；args[0] 是 message；repr 含类名
- **module __all__**：5 元素顺序精确；_schema_path 不导出但可访问
- **签名**：load_schema/validate/validate_file/_schema_path/EvalSchemaError.__init__ 精确

### 撞墙记录
- 2 fail（修复）：
  - test_validate_multi_errors_count_in_message：以为 bad manifest 缺 3 个 required 字段；实际 expected_failures 有默认值（[]），只缺 2 个 → 改成 >= 2
  - test_module_schemas_dir_value：直接用 `evaluation.schema.__file__` 但 evaluation 未导入 → 加 `import evaluation.schema`

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 239 后）：20961 pass / 0 fail / 15 skip（HEAD `4cbd85b`）

### 下一步建议
- 候选 KT2：evaluation/manifest.py 第十四轮（239 行）
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE2（evaluation/annotation_metrics.py 第十三轮）继续推 evaluation 大文件。

---
## Round 240 — evaluation/manifest.py 第十四轮（100 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十四轮 edges 测试，覆盖 _is_absolute_like/_has_backslash 深度边界、_resolve_relative_path field_name 透传、dataclass frozen/hashable/equality、load_manifest 各种边界、_detect_project_root、模块结构

### 改动
- 新增 `tests/test_evaluation_manifest_edges14.py`（100 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like**：'/' True；'/a' True；'a:b' False；'a:' False；'a:\' True；'a:/' True；'a:foo' False；大小写盘符；digit 盘符 False；2/3 字符边界
- **_has_backslash**：空字符串 False；纯正斜杠 False；多个反斜杠 True；mixed True
- **_resolve_relative_path**：field_name 在 empty/absolute/backslash/outside_root 错误消息中；返回绝对路径；在 project_root 内
- **frozen + hashable + equality**：DocumentEntry/ExpectedFailure/Manifest 三个 dataclass 都验证 frozen/hashable/equality/inequality
- **fields() 精确**：DocumentEntry 10 字段；ExpectedFailure 5 字段；Manifest 5 字段；字段名精确
- **Manifest properties 类型**：file_count/pdf_count/docx_count/content_group_count/categories_covered 都返回正确类型
- **categories_covered**：sorted list；跨文档去重
- **load_manifest**：返回 Manifest 实例；documents/expected_failures 是 tuple；project_root 绝对路径；categories list 转 tuple；manifest_version 透传；devset_status 透传
- **Schema 拒绝**：source_type='txt' / devset_status='custom' 都被 schema enum 拒绝
- **ManifestError**：只继承 Exception；init/repr/args；docstring
- **_detect_project_root**：无 pyproject / 在父目录 / 返回绝对路径
- **module __all__**：5 元素顺序精确
- **签名**：load_manifest/_is_absolute_like/_has_backslash/_resolve_relative_path/_detect_project_root 精确

### 撞墙记录
- 2 fail（修复）：
  - test_load_manifest_with_unknown_source_type：以为 source_type='txt' 允许；实际 schema enum 只允许 ['pdf', 'docx'] → 改成 expect EvalSchemaError
  - test_load_manifest_devset_status_propagated：'custom_status' 不是 enum 值 → 改成用 'complete' 验证透传，并加 schema enum 拒绝测试

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 240 后）：21061 pass / 0 fail / 15 skip（HEAD `63076bc`）

### 下一步建议
- 候选 KE2：evaluation/annotation_metrics.py 第十三轮（194 行）
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE2（evaluation/annotation_metrics.py 第十三轮）继续推 evaluation 大文件。

---
## Round 241 — evaluation/annotation_metrics.py 第十三轮（58 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十三轮 edges 测试，覆盖 predicted/gt_positions 算法精确、search_from 推进、chunk_text 算法、greedy 一对一策略、module 导入 identity、docstring algorithm keywords

### 改动
- 新增 `tests/test_annotation_metrics_edges13.py`（58 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **predicted boundary positions**：chunks 各种长度的精确 boundary 位置；最后一个 chunk 不贡献 boundary
- **gt_positions 算法**：marker before/after 在 start/end 触发；多个 marker 顺序
- **search_from 推进**：相同 marker 文本不会重复匹配（被消耗后下一个 anchor 走 missing_markers）
- **chunk_text 算法**：whitespace 归一化；int 输入触发 TypeError（re.sub 拒绝）；None 当空处理
- **multi-chunk distance/tolerance matching**：远距离 marker 触发 missing；tolerance_chars 边界
- **stream composition**：unicode / emoji / 多 chunk 都不崩溃
- **module 导入 identity**：_null/_ratio/normalize_text/Counter 都从源模块直接 import
- **chunk_boundary_prf docstring**：含 algorithm keywords（normalize/greedy/one-to-one/marker/predicted/ground_truth/anchor/algorithm/args）
- **figure_caption_prf docstring**：含 parser/relation/null keywords
- **PARSER_DOES_NOT_EMIT_RELATIONS**：snake_case / lowercase / parser_ 前缀
- **greedy matching strategy**：closest first；不会 double-assign；duplicate marker 走 missing_markers
- **module __all__**：3 元素顺序精确

### 撞墙记录
- 2 fail（修复）：
  - test_greedy_does_not_double_assign_predicted：alpha marker 已被 search_from 消耗，第二个 anchor 走 missing_markers，不是 double-assign → 改成 precision/recall 都 1.0，'alpha' in _missing_markers
  - test_chunk_text_with_int_raises_at_normalize：normalize_text 调 re.sub 在 int 输入触发 TypeError（不是 AttributeError）→ 改成 expect TypeError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 241 后）：21119 pass / 0 fail / 15 skip（HEAD `01772da`）

### 下一步建议
- 候选 KF2：evaluation/metrics.py 第十三轮（381 行）
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF2（evaluation/metrics.py 第十三轮，381 行）继续推 evaluation 最大文件。

---
## Round 242 — evaluation/metrics.py 第十三轮（106 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十三轮 edges 测试，覆盖 _pdf_locator_ratio NaN/Inf bbox、_docx_locator_ratio string substring 行为、_image_resource_ratio truthy 非 str、_chunk_reference_ratio None 边界、_heading_boundary_ratio set 去重、_silent_drop_count truthy 非 dict、_text_preservation whitespace-only/disjoint 字符集、_null/_ratio/_bool_metric/_int_metric 边界、compute_automatic_metrics schema_valid reason 格式、模块结构、签名精确

### 改动
- 新增 `tests/test_evaluation_metrics_edges13.py`（106 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_pdf_locator_ratio**：bbox 含 NaN/+Inf/-Inf 全 rejected；page=999999999 valid；mixed invalid→valid 计数 1/3；all invalid 0.0；缺 source_locator 键；返回 float 类型
- **_docx_locator_ratio**：source_locator='sectionparagraph'（string）触发 substring 检查 → valid；'page1'/'abcbboxXYZ' substring 命中 → invalid；'zzzz' 不命中 → invalid；page=0/bbox=None key 存在 → invalid；relationship_id 字符串值；paragraph_index=None 值 OK；7 个 structural_keys 全在；2 个 keys；mixed invalid→valid 1/3；返回 float
- **_image_resource_ratio**：resource_path=True raises TypeError（bool 不行）；int 1 raises TypeError；3 images 全 valid/全 invalid；element 缺 type 不算 denominator；resource_path 是 Path 对象 OK
- **_chunk_reference_ratio**：source_element_ids=None；chunk 引用 None；element_id=None 在集合中；all chunks valid；多 ID partial invalid；多 ID all valid
- **_heading_boundary_ratio**：2 chunks 同 first_id set 去重；heading 无 element_id 键；heading element_id=None；chunks=[] 仍计算 ratio 不返回 null；2 headings 1 match → 0.5
- **_silent_drop_count**：expectations='abc' raises AttributeError；[] falsy → no_expectations；[1,2] truthy → AttributeError；element_count_by_type=list raises；expected=0/-3 不 drop；actual=0 expected=3 → drop=3；3 type 求和
- **_text_preservation**：actual whitespace-only → empty_actual；expected whitespace-only → empty_expected；both whitespace-only → empty_expected_and_actual；disjoint 字符集 'abc' vs 'xyz' → precision/recall=0；same chars different counts；unicode chars；image excluded 但 chunk 中包含
- **Counter 交集**：空 Counter & 任意 = 空
- **_null 边界**：empty reason；None reason 透传；unicode reason
- **_ratio 边界**：bool True/False 转 float
- **_bool_metric 边界**：truthy/falsy 非 bool 输入；list 输入
- **_int_metric 边界**：bool 输入；float 截断；value 类型是 int 不是 float
- **compute_automatic_metrics**：error={} falsy → error_code=None；error code 是 string/int 透传；schema_valid exception reason 格式精确 'schema_check_exception:TypeName'；exception 类型名透传；真实 schema_validation 不抛；不修改 image_base_dir；expectations='abc' raises
- **element_count_by_type**：插入顺序 = element 出现顺序；同 type 累加保持首次位置
- **模块结构**：__all__ 是 list 不是 tuple；精确 ['compute_automatic_metrics']；Any/math/Counter/Path 在命名空间；_TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED 精确值；subset 关系
- **签名**：所有 14 个函数签名精确（含参数名顺序）

### 撞墙记录
- 2 fail（修复）：
  - test_image_resource_ratio_resource_path_int_one：以为 Path(1) OK；实际 Path(int) raises TypeError → 改成 expect TypeError
  - test_compute_metrics_does_not_mutate_image_base_dir：把 tmp_path 当成 expectations 参数传了；实际 signature 是 (doc, error, source_type, expectations, image_base_dir=None) → 改成 keyword 参数 image_base_dir=tmp_path

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 242 后）：21225 pass / 0 fail / 15 skip（HEAD `0d73642`）

### 下一步建议
- 候选 KW2：evaluation/report.py 第十四轮（200 行）
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW2（evaluation/report.py 第十四轮，200 行）继续推 evaluation 中型文件。

---
## Round 243 — evaluation/report.py 第十四轮（72 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十四轮 edges 测试，覆盖 str project_root 接受、ratio value 边界（>1.0/negative）、per_doc tuple/extra keys、build_devset_section 独立 dict、get_dependency_versions 不缓存、subprocess 调用细节、模块结构精确、签名精确、callable 验证

### 改动
- 新增 `tests/test_evaluation_report_edges14.py`（72 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **str project_root**：build_provenance/get_git_provenance 接受 str；Path-like __fspath__ 对象
- **ratio value 边界**：>1.0 仍参与 macro；negative 仍参与；mixed 计算；extreme large 1e6
- **per_doc_results 类型**：tuple iterable OK；extra keys (doc_id/source_type/errors) 不影响聚合
- **chunk_boundary metrics**：3 个 metric 都参与 ratio_macro
- **silent_drop_total float**：2.5+1.5=4.0（float 求和）
- **count 求和**：negative + positive 混合
- **build_devset_section**：每次返回新 dict；修改不影响 Manifest；devset_status='complete' 透传；categories_covered tuple；negative counts 透传；duck typing
- **get_dependency_versions**：每次返回新 dict；修改不影响下次；PackageNotFoundError 与 Exception 都返回 None；monkeypatch 返回特定值
- **get_git_provenance subprocess**：OSError/SubprocessError 返回 commit=None+dirty=True；两次调用顺序 rev-parse → status；stdout strip whitespace；空白 stdout → None；porcelain 非空 → dirty；returncode 非 0 → dirty=False
- **build_provenance**：每次新 dict（timestamp 可能不同）；evaluator_version/report_version 常量；dependencies dict；dependencies 每次独立；parser_version 透传；max_chars int 转换；negative/zero max_chars；ISO timestamp parseable
- **模块结构**：__all__ 是 list 不是 tuple；__all__ 顺序精确 5 元素；Any/subprocess/datetime/Path 在 namespace identity；3 个 constants 是 tuple；3 个 constants pairwise 不交集
- **签名**：5 个公开函数签名精确
- **callable**：__all__ 中所有元素都 callable；5 个公开函数都 callable
- **顶层结构**：aggregate_summary 4 keys 顺序精确；counts/success_rates/silent_drop_total 必有 key；per_doc 含 None value 不参与 success_count 但仍计入 total

### 撞墙记录
- 0 fail（一次通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 243 后）：21297 pass / 0 fail / 15 skip（HEAD `6161ad1`）

### 下一步建议
- 候选 KX2：evaluation/cli.py 第十五轮（243 行）
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX2（evaluation/cli.py 第十五轮，243 行）继续推 evaluation。

---
## Round 244 — evaluation/cli.py 第十五轮（66 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十五轮 edges 测试，覆盖 _format_metric Counter/dict 特殊键/name unicode/emoji/dict 子类，_build_parser subparser choices 精确，_run_inspect_doc duck typing args，__name__=="__main__" 块，模块无 __all__，argparse 错误退出码

### 改动
- 新增 `tests/test_evaluation_cli_edges15.py`（66 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_format_metric Counter**：Counter（dict 子类）走 dict 分支；空 Counter；带 reason 的 Counter
- **_format_metric dict 特殊键**：int 键 OK；tuple+str 混合 raises TypeError；int+str 混合 raises；None+str 混合 raises；纯 None/纯 int 键 OK
- **_format_metric name 边界**：unicode；emoji；newline；tab 都按字面渲染
- **_format_metric metric 类型**：dict 子类 OK；空 dict → null (None)
- **_format_metric value 边界**：0.0 → 0.0000；-0.0 → -0.0000；1e-10 → 0.0000（精度丢失）；1e10 → 10000000000.0000
- **_format_metric reason 边界**：empty string → ok；0 → ok；'0' → 透传；unicode reason
- **_build_parser subparser**：choices 精确 3 个 {run, validate-report, inspect-doc}；dest='command'；required=True；run 5 user-defined option args；validate 1 positional；inspect 1 positional + 1 user-defined option
- **_run_inspect_doc duck typing**：自定义类含 .input/.tolerance_chars OK；dict args raises AttributeError；args.input=None raises TypeError
- **__name__=="__main__" 块**：源码含 '__name__' '"__main__"' 'SystemExit' 'main()'
- **main 签名**：(argv=None) 单参数；默认 None
- **模块结构**：无 __all__ 属性；argparse/json/sys/Path identity 在 namespace；main/_build_parser/_format_metric/_run_inspect_doc 在 namespace
- **函数签名**：_build_parser() 无参；_format_metric(name, metric)；_run_inspect_doc(args)
- **callable 验证**：4 个公开函数都 callable
- **prog/description/formatter**：prog='evaluation.cli'；description 含 '评测'；formatter_class=RawDescriptionHelpFormatter
- **argparse 错误**：run/validate-report/inspect-doc 各自缺参数 → SystemExit(2)；unknown command → SystemExit(2)；no command → SystemExit(2)

### 撞墙记录
- 2 fail（修复）：
  - test_build_parser_run_subparser_argument_count_four：以为 5 个 user args；实际 argparse 自动加 -h/--help 也算 option_strings → 改成 a.dest != "help" 过滤
  - test_build_parser_inspect_subparser_argument_count_two：同样问题 → 同样过滤 help

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 244 后）：21363 pass / 0 fail / 15 skip（HEAD `ef3b2c1`）

### 下一步建议
- 候选 KS2：evaluation/runner.py 第十五轮（227 行）
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS2（evaluation/runner.py 第十五轮，227 行）继续推 evaluation。

---
## Round 245 — evaluation/runner.py 第十五轮（59 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十五轮 edges 测试，覆盖模块 namespace identity（Any/json/time/Path/REPORT_VERSION）、REPORT_VERSION identity、__all__ 精确、模块源码字符串、_load_annotation OSError 处理、_process_one 错误路径与 image_dir、run_evaluation signature keyword-only 标记

### 改动
- 新增 `tests/test_evaluation_runner_edges15.py`（59 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **namespace identity**：typing.Any / json / time / Path 在 namespace；REPORT_VERSION 在 namespace 且 is evaluation.REPORT_VERSION
- **__all__**：是 list；精确 ['run_evaluation']；不含 _load_annotation / _process_one；内部 helper 仍可访问
- **模块源码字符串**：docstring 含 not_instrumented / process_single / image_output_dir / pipeline_failed / per_doc；源码含 not_instrumented / image_output_dir_for( / perf_counter
- **_load_annotation**：None path → None；不存在 → None；目录 → None；合法 dict/list → 返回；非法 JSON → None；空文件 → None；OSError 时不抛
- **_load_annotation signature**：(path) 单参；return annotation str 含 dict+None
- **_process_one signature**：4 参精确；return annotation 5-tuple；所有参数无默认
- **run_evaluation signature**：5 参精确；3 个 keyword-only（parser_name/max_chars/tolerance_chars）；2 个 positional（manifest/output_path）；默认值精确；return dict
- **callable**：3 个函数都 callable
- **端到端**：report 顶层 6 keys 顺序精确；report_version=常量；空 manifest → per_doc/expected_failures=[]；summary 4 keys；devset 6 keys；provenance 9 keys；返回 dict == 文件内容；output_path 自动创建目录
- **devset 透传**：devset_status='complete'；categories_covered list
- **process_one 错误路径**：document=None + 无 errors → unknown 错误；errors list 取第一个；创建 _per_doc 子目录；elapsed ≥ 0；image_dir=None on failure；清理 stub 文件
- **keyword-only 验证**：keyword 参数 OK；默认值 OK

### 撞墙记录
- 1 fail（修复）：
  - test_run_evaluation_devset_categories_propagated：多写了逗号 `["math", "science"],` → 变成 tuple → 去掉末尾逗号

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 245 后）：21422 pass / 0 fail / 15 skip（HEAD `7bd7691`）

### 下一步建议
- 候选 KZ2：evaluation/schema.py 第八轮（80 行）
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ2（evaluation/schema.py 第八轮，80 行）继续推 evaluation 最小文件。

---
## Round 246 — evaluation/schema.py 第八轮（80 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第八轮 edges 测试，覆盖 namespace identity、__all__ 精确、模块 docstring、EvalSchemaError 详细行为、_schema_path 路径穿越/绝对路径/空名、validate 返回 None / 不修改 instance、validate_file JSONDecodeError 透传、签名精确

### 改动
- 新增 `tests/test_evaluation_schema_edges8.py`（81 测试，1 个 Windows 上 skipped）
- 仅测试，不动业务代码

### 覆盖要点
- **namespace identity**：typing.Any / json / Path / Draft202012Validator / JSValidationError 都 is 源模块
- **SCHEMAS_DIR 精确**：是 Path；绝对路径；值匹配；目录存在；4 个 schema 文件存在
- **__all__**：是 list；5 元素顺序精确；无重复；不含私有 _schema_path
- **模块 docstring**：含 manifest / annotation / evaluation-report；提到不与 app/schema 复用
- **EvalSchemaError**：继承 Exception；errors 默认 []；errors=None → []；errors=[] → []；errors kwarg 透传（同 list 引用）；errors 可 mutate；message attribute；str/repr；可 raise/except；__init__ 签名 (self, message, errors=None)
- **_schema_path**：dotdot 路径穿越 raises；subdir raises；.json raises；空 name raises；大写 name Windows 上不抛；error message 含 schema 名字；4 个已知 schema 返回 Path；返回的 Path 在 SCHEMAS_DIR 内；签名精确
- **load_schema**：返回 dict；不缓存（每次新 dict）；修改不影响下次；4 个已知 schema 都返回 dict 含 $schema；签名精确
- **validate**：成功返回 None；不修改 instance；错误 message 含 path= / schema_name；errors 每项 3 key；path/schema_path 是 list；签名精确
- **validate_file**：接受 str/Path；返回 None on success；missing raises；directory raises；invalid JSON raises JSONDecodeError；invalid content raises EvalSchemaError；utf-8 OK；含中文 OK；签名精确
- **callable**：5 个公开 symbol 都 callable
- **Draft202012Validator 集成**：load_schema 返回可被 Validator 使用；validate 与直接 Validator 行为一致；4 个 schema 自身合法

### 撞墙记录
- 3 fail（修复）：
  - test_schema_path_uppercase_name_raises：Windows 文件系统 case-insensitive，大写名字仍匹配 → 加 skip 标记
  - test_validate_return_annotation_is_none：from __future__ import annotations 让 return_annotation 是字符串 'None' 不是 None → 改成 `is None or == 'None'`
  - test_validate_file_return_annotation_is_none：同上

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 246 后）：21502 pass / 0 fail / 16 skip（HEAD `faf5c9f`）

### 下一步建议
- 候选 KT3：evaluation/manifest.py 第十五轮（239 行）
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT3（evaluation/manifest.py 第十五轮，239 行）继续推 evaluation。

---
## Round 247 — evaluation/manifest.py 第十五轮（90 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十五轮 edges 测试，覆盖 namespace identity、__all__ 精确、模块 docstring、ManifestError 详细行为、_is_absolute_like/_has_backslash 边界、_resolve_relative_path 错误消息含字段名、_detect_project_root、DocumentEntry/ExpectedFailure/Manifest dataclass frozen+字段精确、Manifest properties、签名精确

### 改动
- 新增 `tests/test_evaluation_manifest_edges15.py`（90 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **namespace identity**：typing.Any / dataclass / Path / json / MANIFEST_VERSION / validate 都 is 源模块/对象
- **MANIFEST_VERSION**：值 '1.0'；是 str
- **__all__**：是 list；5 元素顺序精确 [ManifestError, Manifest, DocumentEntry, ExpectedFailure, load_manifest]；无重复；不含私有 helper
- **模块 docstring**：含 'relative' / 'absolute' / 'backslash' / 'project root'
- **ManifestError**：继承 Exception 不继承 ValueError；默认无 errors；errors kwarg 透传；message attribute；str/repr；可 raise/except
- **_is_absolute_like 边界**：空 / 单斜杠 / 反斜杠 / alpha:backslash / alpha:slash / alpha:only / alpha:letter / 数字 colon / 2-3 字符边界
- **_has_backslash 边界**：空 / 仅正斜杠 / 单反斜杠 / 多反斜杠 / 混合 / 仅反斜杠
- **_resolve_relative_path 错误消息**：含字段名（empty/absolute/backslash/outside_root）；成功返回绝对路径在 project_root 下；unicode filename
- **_detect_project_root**：pyproject 在 self/parent；无 pyproject raises；file 起始；返回绝对路径
- **dataclass frozen**：DocumentEntry / ExpectedFailure / Manifest 都 frozen=True；字段数精确；字段名顺序精确；hashable
- **Manifest properties**：file_count/pdf_count/docx_count/content_group_count/categories_covered 返回类型
- **categories_covered**：空 / sorted-unique / case-sensitive / unicode
- **签名精确**：load_manifest(manifest_path, project_root=None)；_is_absolute_like(name)；_has_backslash(name)；_resolve_relative_path(name, project_root, field_name)；_detect_project_root(path)
- **callable**：5 个公开 symbol 都 callable
- **End-to-end**：missing file/directory/invalid JSON raises ManifestError；返回 Manifest 实例；manifest_version 透传；documents 是 tuple；project_root 是 Path

### 撞墙记录
- 0 fail：90 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 247 后）：21592 pass / 0 fail / 16 skip（HEAD `6ba49ee`）

### 下一步建议
- 候选 KE3：evaluation/annotation_metrics.py 第十四轮（194 行）
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE3（evaluation/annotation_metrics.py 第十四轮，194 行）继续推 evaluation。

---
## Round 248 — evaluation/annotation_metrics.py 第十四轮（86 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十四轮 edges 测试，覆盖源码字符串断言（inspect.getsource）、模块/函数 metadata、__future__ annotations 影响、bytes/bytearray marker/text TypeError、anchor 缺 key 默认行为、dict subclass / tuple chunks、_tolerance_chars value 类型精确、reason 字符串精确、输出 key 集合精确、签名参数 kind 精确

### 改动
- 新增 `tests/test_annotation_metrics_edges14.py`（86 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言（inspect.getsource）**：含 '.find(' / 'normalize_text' / '_null(' / '_ratio(' / 'PARSER_DOES_NOT_EMIT_RELATIONS' / 'marker' / 'anchor' / 'tolerance_chars'；不含 '__main__'；含 'from __future__ import annotations'；含 'dict[str,'；含 'tolerance_chars: int = 30'
- **模块 metadata**：__file__ 后缀 .py；含 'annotation_metrics'；__package__ == 'evaluation'；__name__ == 'evaluation.annotation_metrics'；__all__ 是 list 不是 tuple；Counter 在命名空间且 is collections.Counter；Counter 在源码 body 中无调用（仅 import）
- **函数 metadata**：__module__/__qualname__/__name__ 精确；都是 types.FunctionType；无 varargs/varkw；return_annotation 是 str（来自 __future__）含 'dict'
- **bytes/bytearray marker**：stream.find(bytes) raises TypeError；bytearray 同样；chunk text 是 bytes/bytearray 同样 raises TypeError
- **anchor 缺 key 默认**：缺 marker → '' → missing_markers；缺 position → 'after' 默认；含 extra unknown key 静默忽略；空 dict {} → '' + 'after' 默认
- **dict subclass / tuple chunks**：DocSub(dict) 工作；AnnSub(dict) 工作；chunks 是 tuple 工作；chunks 是 generator raises TypeError（len 失败）；chunk_boundary_anchors 是 tuple 工作
- **PARSER_DOES_NOT_EMIT_RELATIONS 详细**：是 str；值精确 'parser_does_not_emit_relations'；无空格/连字符/点；在 namespace；在 __all__
- **_tolerance_chars value 类型**：默认 30 是 int；0/-1/99999 都透传 int
- **输出 keys 集合**：有 missing_markers 时 5 keys；无 missing_markers 时 4 keys；figure_caption_prf 始终 3 keys
- **figure_caption_prf 详细**：所有 value 是 None；所有 reason 同常量；keys 顺序 [precision, recall, f1]；不修改输入
- **chunk_boundary_prf 一致性**：不修改 document/annotation
- **reason 精确**：no_predicted_boundaries / no_ground_truth_anchors / pipeline_failed / no_annotation / no_ground_truth_anchors_in_stream 都精确等值
- **算法一致性**：stream = normalize_text(' '.join(normalize_text(chunk_text)))；chunks 含 leading/trailing whitespace 正确处理
- **签名参数 kind**：chunk_boundary_prf 3 个 POSITIONAL_OR_KEYWORD（无 * 分隔）；figure_caption_prf 2 个 POSITIONAL_OR_KEYWORD；tolerance_chars default 30；前 2 个无 default；figure_caption_prf 无 default
- **边界**：所有 chunks 文本为空字符串；chunks 混入 None text

### 撞墙记录
- 2 fail（修复）：
  - test_chunks_generator_exhausted_in_first_iteration：generator 无 len() → 源码 `len(chunks) < 2` raises TypeError → 改测试为期望 TypeError
  - test_chunk_boundary_prf_param_kinds：tolerance_chars 是 POSITIONAL_OR_KEYWORD（无 * 分隔符），不是 KEYWORD_ONLY → 改为 all POSITIONAL_OR_KEYWORD

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 248 后）：21678 pass / 0 fail / 16 skip（HEAD `d79cd7d`）

### 下一步建议
- 候选 KF3：evaluation/metrics.py 第十四轮（381 行）
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF3（evaluation/metrics.py 第十四轮，381 行）继续推 evaluation 最大文件。

---
## Round 249 — evaluation/metrics.py 第十四轮（152 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十四轮 edges 测试，覆盖源码字符串断言、模块/函数 metadata、signature 无 varargs/varkw、__future__ annotations 影响、常量精确（_TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED）、_is_valid_bbox 边界、_strip_unicode_whitespace 字符级、_null/_ratio/_bool_metric/_int_metric 不缓存、_image_resource_ratio directory 与 size=0 处理、_chunk_reference_ratio 边界、_silent_drop_count actual>expected 行为、_pdf/_docx_locator_ratio 边界、_text_preservation 空字符串/null reason 精确

### 改动
- 新增 `tests/test_evaluation_metrics_edges14.py`（152 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 '_TEXT_TYPES' / '_PDF_BBOX_REQUIRED_TYPES' / '_NOT_EVALUATED' / Counter/Path/math import / future annotations / dict[str, / schema_validation lazy import / 'if actual < exp' / 'v1.1' 注释 / 'math.isfinite'；不含 '__main__'
- **模块 metadata**：__file__ 后缀 .py / 含 'metrics'；__package__=='evaluation'；__name__=='evaluation.metrics'；Counter/Path/math identity
- **__all__ 精确**：仅 1 个元素 ['compute_automatic_metrics']；不含 helper；是 list 不是 tuple
- **常量精确**：_TEXT_TYPES 是 tuple / 7 个元素 / 内容顺序精确 / 无重复；_PDF_BBOX_REQUIRED_TYPES 4 个 / ⊆ _TEXT_TYPES / 排除 table/header/footer；_NOT_EVALUATED == 'not_evaluated'
- **函数 metadata**：__module__/__qualname__/__name__ 精确；都是 FunctionType；无 varargs/varkw；return_annotation 是 str（来自 __future__）
- **_null/_ratio/_bool_metric/_int_metric**：每次返回新 dict（不缓存）
- **_is_valid_bbox 边界**：float/int/混合 接受；bool True/False 拒绝；length 3/5/0 拒绝；tuple/None/str 拒绝；Inf/-Inf/NaN 拒绝；负数/0/大数接受；返回 bool 类型
- **_strip_unicode_whitespace 字符级**：NBSP/em/en space/全角空格/line separator/paragraph separator 都删除；普通 \t/\n/\r/\f/\v 删除；ZWSP 不算空白（按 Python 行为）；保留非空白字符；空字符串；全空白；bytes raises AttributeError（int 无 isspace）；不排序；返回 str
- **_image_resource_ratio**：directory 不算 file → invalid；size=0 invalid；size=1 valid；3 个全 valid → 1.0；mixed → 2/3；resource_path key 缺失/空字符串/None 都跳过；无 images → 'no_image_elements'；相对路径 + image_base_dir 拼接
- **_chunk_reference_ratio**：空 chunks → 'no_chunks'；source_element_ids=[None] 时 None in {None} True；空 list/缺 key → 跳过；partial valid → 0.0；全 valid → 1.0
- **_silent_drop_count**：actual>expected 不扣（max(0,exp-act)）；actual==expected 0；多类型 sum；expected type missing in actual → drop；no expectations/empty expectations/empty counts 都 null
- **_pdf_locator_ratio**：空 → 'no_elements'；paragraph/caption/list_item 需 bbox；table/header/footer 不需 bbox；source_locator=None/missing 都 invalid；page float 拒绝；page bool=True 接受（bool 是 int 子类，True==1）
- **_docx_locator_ratio**：空 → 'no_elements'；7 个 structural key 都单独 valid；含 page 或 bbox → invalid；source_locator=None/missing/empty 都 invalid
- **_text_preservation**：都空 → 'empty_expected_and_actual'；只 image elements → expected=''；chunk text None → actual=''；element content None → expected=''；返回 dict 3 keys
- **_heading_boundary_ratio**：无 heading → 'no_heading_elements'；heading 是 chunk 第一个 → valid；不是第一个 → invalid；有 heading 但无 chunks → 0.0（不是 'no_chunks'）；空 source_element_ids 跳过
- **compute_automatic_metrics**：doc=None 时 14 个 keys；后续 11 metric 都 'pipeline_failed'；不修改输入 document/expectations

### 撞墙记录
- 1 fail（修复）：
  - test_strip_unicode_whitespace_bytes_raises_type_error：bytes 迭代给 int，int 无 isspace() → AttributeError（不是 TypeError）→ 改成期望 AttributeError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 249 后）：21830 pass / 0 fail / 16 skip（HEAD `8ba79be`）

### 下一步建议
- 候选 KW3：evaluation/report.py 第十五轮（200 行）
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW3（evaluation/report.py 第十五轮，200 行）继续推 evaluation。

---
## Round 250 — evaluation/report.py 第十五轮（104 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十五轮 edges 测试，覆盖源码字符串断言、模块/函数 metadata、signature 无 varargs/varkw、__future__ annotations 影响、常量精确（_RATIO_METRICS 12 个/_COUNT_METRICS 1 个/_SUCCESS_BOOL_METRICS 1 个）+ 互不相交 + 总 14 个、build_provenance 9 keys 顺序精确、build_devset_section 6 keys 顺序精确、aggregate_summary 4 top-level keys 顺序精确 + 各 sub-dict 结构精确

### 改动
- 新增 `tests/test_evaluation_report_edges15.py`（104 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 '_RATIO_METRICS' / '_COUNT_METRICS' / '_SUCCESS_BOOL_METRICS' / 'subprocess.run(' / 'datetime.now().astimezone()' / 'import importlib.metadata' / future annotations / 'dict[str,' / 'EVALUATOR_VERSION' / 'REPORT_VERSION' / 'capture_output=True' / 'timeout=10' / 'silent_drop_total' / 'ratio_macro_averages' / 'success_rates'；不含 '__main__'
- **模块 metadata**：__file__ 后缀 .py / 含 'report'；__package__=='evaluation'；__name__=='evaluation.report'；subprocess/datetime/Path/Any identity；EVALUATOR_VERSION/REPORT_VERSION is
- **__all__ 精确**：是 list 不是 tuple；集合精确 5 个；不含私有；不含 _RATIO_METRICS/_COUNT_METRICS/_SUCCESS_BOOL_METRICS；所有名字在命名空间
- **常量精确**：_COUNT_METRICS 1 个 'element_count_total'；_SUCCESS_BOOL_METRICS 1 个 'pipeline_success'；_RATIO_METRICS 12 个顺序精确；无 figure_caption_*；无 silent_drop_count；3 个常量互不相交；总和 14
- **函数 metadata**：5 个公开函数 __module__/__qualname__/__name__ 精确；都是 FunctionType；无 varargs/varkw；return_annotation 是 str（__future__）
- **build_provenance 输出**：9 keys 顺序精确；返回 dict；max_chars 是 int；parser_name 透传；parser_version=None 接受；evaluator_version/report_version 是常量；dependencies 3 keys；run_timestamp_iso 是 str
- **build_devset_section 输出**：6 keys 顺序精确；返回 dict；categories_covered 透传
- **aggregate_summary 输出**：4 top-level keys 顺序精确 [counts, success_rates, ratio_macro_averages, silent_drop_total]；counts 1 key；success_rates 1 key；ratio_macro_averages 12 keys；空输入 silent_drop_total=None / counts.sum=None / success rate=None / 每个 ratio macro_average=None
- **aggregate_summary counts**：sum 是 int；None value 不参与
- **aggregate_summary success_rates**：rate = successes/total；只 True 计入 success_count；False/None 不计
- **aggregate_summary ratio_macro_averages**：macro_average = mean；not_evaluated = total - participating
- **aggregate_summary silent_drop_total**：sum；None 不参与；全 None → None；缺 key → None
- **get_dependency_versions**：3 keys 集合精确；返回 dict；value 是 str/None；不含 'docx'/'kreuzberg'
- **get_git_provenance**：返回 2 keys；返回 dict；git_dirty 是 bool；git_commit 是 str/None
- **aggregate_summary tuple 输入**：tuple 工作；空 tuple 工作；不修改输入

### 撞墙记录
- 0 fail：104 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 250 后）：21934 pass / 0 fail / 16 skip（HEAD `7e45dfe`）

### 下一步建议
- 候选 KX3：evaluation/cli.py 第十六轮（243 行）
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX3（evaluation/cli.py 第十六轮，243 行）继续推 evaluation。

---
## Round 251 — evaluation/cli.py 第十六轮（107 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十六轮 edges 测试，覆盖源码字符串断言（inspect.getsource 含特定 token）、模块/函数 metadata、__future__ annotations 影响、_format_metric 各分支精确（bool/float/dict/int/str/None）、_run_inspect_doc 输出格式精确（file/document_id/source/parser/counts/metrics）、argparse run_p 4 个 argument 的 default 与 required 精确、main 子命令分发返回值、main signature 单参数 argv 默认 None、argparse 错误处理 SystemExit(2)

### 改动
- 新增 `tests/test_evaluation_cli_edges16.py`（107 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 '--manifest'/'--output'/'--parser'/'--max-chars'/'--tolerance-chars'/'fallback'/'kreuzberg'/'default=800'/'default=30'/'add_parser("run"'/'validate-report'/'inspect-doc'/'add_subparsers'/'import argparse'/'def main('/'def _run_inspect_doc('/'def _format_metric('/'choices='/'return 0'/'return 1'/'return 2'/'raise SystemExit(main())'/'if __name__ == "__main__":'
- **模块 metadata**：__file__ 后缀 .py / 含 'cli'；__package__=='evaluation'；__name__=='evaluation.cli'；argparse/json/sys/Path identity；namespace 含 main/_build_parser/_format_metric/_run_inspect_doc；不含顶层 'run'
- **函数 metadata**：main/_build_parser/_format_metric/_run_inspect_doc __module__/__qualname__ 精确；都是 FunctionType；main 无 varargs/varkw；_build_parser 无参数；return_annotation 是 str
- **_format_metric 各分支**：value=None 渲染 'null'；True/False 渲染小写；int/float/dict/str 各分支；float 渲染 4 位小数；dict items 排序；dict 空 items；reason 替换 'ok'；name 字段宽度 36；unicode name；长 name 不截断
- **argparse 结构**：prog='evaluation.cli'；description 含 '评测 CLI'；run --parser choices=('fallback', 'kreuzberg')；run --parser default='fallback'；run --max-chars default=800；run --tolerance-chars default=30；inspect-doc --tolerance-chars default=30；run --manifest/--output required=True；validate-report/inspect-doc input positional
- **main signature**：1 个参数 'argv'；POSITIONAL_OR_KEYWORD；默认 None；return annotation 含 'int'
- **_run_inspect_doc 输出**：含 'file:' / 'document_id:' / 'source:' / 'parser:' / 'counts:' / 'metrics:'；返回 0 成功 / 2 文件不存在 / 1 非法 JSON / 1 非 dict
- **main 子命令分发**：run 不存在 manifest → 2；validate-report 不存在 → 2；inspect-doc 不存在 → 2
- **argparse 错误**：未知 --parser choice → SystemExit(2)；--max-chars 非数字 → SystemExit(2)；未知参数 → SystemExit(2)
- **模块无 __all__**

### 撞墙记录
- 0 fail：107 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 251 后）：22041 pass / 0 fail / 16 skip（HEAD `e3c090f`）

### 下一步建议
- 候选 KS3：evaluation/runner.py 第十六轮（227 行）
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS3（evaluation/runner.py 第十六轮，227 行）继续推 evaluation。

---
## Round 252 — evaluation/runner.py 第十六轮（88 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十六轮 edges 测试，覆盖源码字符串断言、模块/函数 metadata、__future__ annotations 影响、_load_annotation 边界（BOM/unicode 文件名/不同输入）、_process_one 签名精确、run_evaluation keyword-only 标记精确、report 6 top-level keys 顺序精确、写盘 JSON 与返回 dict 一致（含 tuple→list 序列化）

### 改动
- 新增 `tests/test_evaluation_runner_edges16.py`（88 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 'process_single' / 'image_output_dir_for' / 'perf_counter' / 'REPORT_VERSION' / 'aggregate_summary' / 'build_devset_section' / 'build_provenance' / 'chunk_boundary_prf' / 'figure_caption_prf' / 'compute_automatic_metrics' / 'not_instrumented' / '_per_doc' / 'parse_reason' / 'chunk_reason' / 'json.dump' / future annotations / 'dict[str,' / 'image_dir' / 'doc_id'；不含 '__main__'
- **模块 metadata**：__file__ 后缀 .py / 含 'runner'；__package__=='evaluation'；__name__=='evaluation.runner'；json/Path/Any/time identity；REPORT_VERSION is 常量
- **__all__ 精确**：是 list 不是 tuple；仅 1 个元素 ['run_evaluation']；不含 _load_annotation / _process_one
- **函数 metadata**：3 个函数 __module__/__qualname__ 精确；都是 FunctionType；无 varargs/varkw；return_annotation 是 str
- **_load_annotation 边界**：None 输入；missing 文件；directory；valid dict/list；invalid JSON；empty 文件；utf-8 BOM（源码用 'utf-8' 不剥 BOM → JSONDecodeError → None）；unicode 文件名；每次新 dict；接受 Path 对象；signature 1 个参数 'path'
- **_process_one 签名**：4 个参数 [doc, output_root, parser_name, max_chars]；全 POSITIONAL_OR_KEYWORD；无 default
- **run_evaluation 签名**：5 个参数；前 2 个 POSITIONAL_OR_KEYWORD；后 3 个 KEYWORD_ONLY；defaults 'fallback'/800/30；前 2 个无 default
- **run_evaluation 输出结构**：6 top-level keys 顺序精确 [report_version, provenance, devset, summary, per_doc, expected_failures]；report_version==REPORT_VERSION；per_doc/expected_failures 是 list；summary/devset/provenance 是 dict；返回 dict；写盘 JSON 与返回 dict 一致（tuple→list）；多级嵌套目录自动创建；空 manifest → per_doc=[]/expected_failures=[]
- **namespace**：含 run_evaluation/_load_annotation/_process_one；不含 'main'

### 撞墙记录
- 2 fail（修复）：
  - test_load_annotation_utf8_bom：源码用 encoding='utf-8' 不剥 BOM → JSONDecodeError 被捕获 → 返回 None（不是 dict）→ 改成期望 None
  - test_run_evaluation_file_matches_returned_report：JSON 序列化把 tuple () 转成 list []，所以直接 == 失败；改成 report_normalized = json.loads(json.dumps(report)) 后再比较

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 252 后）：22129 pass / 0 fail / 16 skip（HEAD `6ecd202`）

### 下一步建议
- 候选 KZ3：evaluation/schema.py 第九轮（80 行）
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ3（evaluation/schema.py 第九轮，80 行）继续推 evaluation。

---
## Round 253 — evaluation/schema.py 第九轮（115 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第九轮 edges 测试，覆盖源码字符串断言（inspect.getsource）、模块/函数/EvalSchemaError class metadata、__future__ annotations 影响、SCHEMAS_DIR 路径解析、_schema_path 边界、load_schema 不缓存、validate errors 结构精确、validate_file 边界

### 改动
- 新增 `tests/test_evaluation_schema_edges9.py`（115 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 'SCHEMAS_DIR' / 'class EvalSchemaError' / 'def _schema_path' / 'def load_schema' / 'def validate(' / 'def validate_file' / 'Draft202012Validator' / 'ValidationError as JSValidationError' / future annotations / 'dict[str,' / 'iter_errors' / 'absolute_path' / '.resolve()' / '.is_file()' / 'raise FileNotFoundError' / 'json.load(' / 'encoding="utf-8"'；不含 '__main__'
- **模块 metadata**：__file__ 后缀 .py / 含 'schema'；__package__=='evaluation'；__name__=='evaluation.schema'；json/Path/Any/Draft202012Validator/JSValidationError identity
- **SCHEMAS_DIR**：Path 实例；绝对路径；resolved 无 '..'；.parent == project_root；.name == 'schemas'；是目录；含 4 个 schema 文件
- **__all__ 精确**：是 list 不是 tuple；5 个元素；集合精确；无重复；不含私有；不含 _schema_path；所有名字在 namespace
- **EvalSchemaError class metadata**：__module__/__qualname__/__name__ 精确；是 Exception 子类；不是 ValueError；mro 含 Exception/BaseException/object；mro 长度 4；__init__ 签名 (self, message, errors=None)；errors default None
- **函数 metadata**：4 个函数 __module__/__qualname__ 精确；都是 FunctionType；无 varargs/varkw；return_annotation 是 str（或 None）
- **_schema_path**：1 参数 'name'；4 个已知 schema 返回 Path 在 SCHEMAS_DIR 下；FileNotFoundError message 含 'Schema'/文件名；dotdot/subdir/empty/.json/manifest 无 ext 都 raises
- **load_schema**：返回 dict；每个含 '$schema' key；不缓存；修改不影响下次；1 参数 'name' POSITIONAL_OR_KEYWORD 无 default
- **validate**：2 参数 (instance, schema_name)；成功返回 None；不修改 instance；非法 raises EvalSchemaError；message 含 schema_name/'path='/'处'；errors 每项 3 key (path/message/schema_path) 都是 list/str；errors 数量与 jsonschema iter_errors 一致
- **validate_file**：接受 str/Path；返回 None；missing/directory raises FileNotFoundError；invalid JSON raises JSONDecodeError；invalid content raises EvalSchemaError；2 参数 (path, schema_name)
- **4 个 schema 自身合法**：Draft202012Validator.check_schema 都通过；与直接 Validator 行为一致

### 撞墙记录
- 2 fail（修复）：
  - test_schemas_dir_parent_parent_is_project_root：SCHEMAS_DIR.parent.parent 是 project_root.parent（Desktop），不是 project_root；改成 SCHEMAS_DIR.parent == project_root
  - test_eval_schema_error_mro_length_three：mro 含 BaseException（4 个不是 3 个）；改成期望 4，并新增 BaseException 检查

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 253 后）：22244 pass / 0 fail / 16 skip（HEAD `8c4f6ea`）

### 下一步建议
- 候选 KT4：evaluation/manifest.py 第十六轮（239 行）
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT4（evaluation/manifest.py 第十六轮，239 行）继续推 evaluation。

---
## Round 254 — evaluation/manifest.py 第十六轮（134 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十六轮 edges 测试，覆盖源码字符串断言（inspect.getsource 含特定 token）、模块/函数/class metadata、dataclass frozen=True 验证、DocumentEntry/ExpectedFailure/Manifest 字段数与名字精确、_is_absolute_like/_has_backslash 边界、_resolve_relative_path 详细、_detect_project_root 各种场景、Manifest properties（pdf_count/docx_count/categories_covered 排序/case-sensitive/unicode/content_group_count 配对逻辑）、load_manifest 端到端边界

### 改动
- 新增 `tests/test_evaluation_manifest_edges16.py`（134 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串断言**：含 'class ManifestError' / 'def _is_absolute_like' / 'def _has_backslash' / '@dataclass(frozen=True)' / 'class DocumentEntry/ExpectedFailure/Manifest' / 'def _resolve_relative_path' / 'def load_manifest' / 'def _detect_project_root' / future annotations / 'pyproject.toml' / 'MANIFEST_VERSION' / 'from evaluation.schema import validate' / 'paired_with' / 'content_group_count' / 'categories_covered' / '.resolve()' / 'relative_to(' / 'field_name'；不含 '__main__'
- **模块 metadata**：__file__ 后缀 .py / 含 'manifest'；__package__=='evaluation'；__name__=='evaluation.manifest'；json/dataclass/Path/Any/MANIFEST_VERSION identity
- **__all__ 精确**：是 list 不是 tuple；集合精确 5 个；不含私有；不含 4 个 helper；所有名字在 namespace；4 个 helper 在 namespace
- **class metadata**：ManifestError/DocumentEntry/ExpectedFailure/Manifest __module__/__qualname__/__name__ 精确；ManifestError mro 长度 4 含 Exception
- **dataclass frozen 验证**：3 个类都 frozen=True；DocumentEntry 10 字段名顺序精确；ExpectedFailure 5 字段；Manifest 5 字段；都可 hash；frozen 阻止 setattr
- **函数 metadata**：load_manifest/_is_absolute_like/_has_backslash/_resolve_relative_path/_detect_project_root __module__/__qualname__ 精确；都是 FunctionType；无 varargs/varkw；return_annotation 是 str；load_manifest 2 参数 (manifest_path, project_root)，project_root default None
- **_is_absolute_like 边界**：相对路径 False；POSIX/Windows 绝对 True；alpha: 后无 / 或 \ False；返回 bool 类型
- **_has_backslash 边界**：无反斜杠 False；有反斜杠 True；返回 bool 类型
- **_resolve_relative_path 详细**：返回 Path 绝对路径；子目录 OK；错误 message 含 field_name；outside root raises；unicode 文件名 OK
- **_detect_project_root 详细**：find pyproject.toml in self/parent；无 pyproject 返回 cur；file start 取 parent；返回绝对路径与 Path 实例
- **Manifest properties 详细**：pdf_count/docx_count/file_count 计算；categories_covered 排序+唯一+空+case-sensitive+unicode；content_group_count 各种 pair 组合（无 pair=每 1 组；1 pair=1 组；mixed）；返回类型 int/list；每次新 list
- **ManifestError 行为**：str/repr；可 raise/except；args()
- **load_manifest 端到端**：missing/directory/invalid JSON/empty file 都 raises；str 路径/project_root 接受；返回 Manifest 实例；documents/expected_failures 是 tuple；project_root 是 Path；manifest_version/devset_status 透传

### 撞墙记录
- 0 fail：134 测试一次性全过（修复了 1 个 SyntaxWarning：docstring 含 '\ ' 改用 r-string）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 254 后）：22378 pass / 0 fail / 16 skip（HEAD `72fc11a`）

### 下一步建议
- 候选 KE4：evaluation/annotation_metrics.py 第十五轮（194 行）
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE4（evaluation/annotation_metrics.py 第十五轮，194 行）继续推 evaluation。

---
## Round 255 — evaluation/annotation_metrics.py 第十五轮（65 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十五轮 edges 测试，覆盖源码字符串断言（inspect.getsource 含特定 token）、模块/函数 metadata、chunk_boundary_anchors 非列表类型边界、annotation 缺 key 与空 anchors、unicode 文本边界（surrogate pairs/ZWJ sequences/control chars/unicode whitespace）、_tolerance_chars/_missing_markers dict 结构、default tolerance_chars=30、figure_caption_prf 各种输入、chunk list/anchors list 引用不变、模块 namespace identity、签名 introspection、PARSER_DOES_NOT_EMIT_RELATIONS hashability/singleton、normalize TypeError on float/dict/list text、`_` 前缀私有 key 验证

### 改动
- 新增 `tests/test_annotation_metrics_edges15.py`（65 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **chunk_boundary_anchors 非列表类型**：None/int/string/set/dict 都返回 None + reason（不抛错）
- **annotation 缺 key / 空 anchors list**：缺失 'chunks'/'anchors'/'markers' 任一返回 None + reason；空 anchors list 返回 None + reason
- **chunk text unicode 边界**：surrogate pairs / ZWJ sequences / 混合 unicode / 控制字符 / unicode whitespace（NBSP/em/en/全角/line sep/para sep/ZWSP）正确处理
- **_tolerance_chars / _missing_markers dict 结构**：每项是 dict；含 'value' 与 'reason' 两个 key；value 类型正确；reason 是 str；只在 namespace 中以 `_` 开头的两个 key
- **default tolerance_chars=30**：默认值精确 30；可以是 keyword arg
- **figure_caption_prf 各种输入**：dict / 非 dict / list / int / None；缺 key 返回 None + reason
- **chunk list / anchors list 引用不变**：调用前后 list id 不变；不修改输入
- **模块 namespace identity**：Any / normalize_text / _null / _ratio / Counter identity
- **签名 introspection**：函数签名返回 inspect.Signature；参数数量；参数名
- **PARSER_DOES_NOT_EMIT_RELATIONS**：可 hash；singleton（多次访问同一对象）
- **normalize TypeError**：float/dict/list 文本在 normalize_text 中抛 TypeError
- **repeated markers 行为**：markers 重复时 chunk_boundary_prf 仍正常返回（去重处理）
- **chunks text 仅数字**：纯数字文本不抛错；返回 None + reason（无 markers 匹配）

### 撞墙记录
- 0 fail：65 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 255 后）：22443 pass / 0 fail / 16 skip（HEAD `4816387`）

### 下一步建议
- 候选 KF4：evaluation/metrics.py 第十五轮（381 行）
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF4（evaluation/metrics.py 第十五轮，381 行）继续推 evaluation。

---
## Round 256 — evaluation/metrics.py 第十五轮（216 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十五轮 edges 测试，覆盖未覆盖的源码字符串 token（含各 helper def + 关键 token）、模块 docstring 长度/内容、compute_automatic_metrics keys 顺序精确、_null/_ratio/_bool_metric/_int_metric dict 字段名精确+顺序、_strip_unicode_whitespace bytes/int/None raises + 多 Unicode 空白字符、_is_valid_bbox 类型边界（tuple/dict/set/string/None/bool/NaN/Inf/-Inf）、_pdf_locator_ratio 边界（page=0/-1/1/True/1.0/string）、_docx_locator_ratio 边界（structural_keys 全检查 + page/bbox 拒绝）、_chunk_reference_ratio 边界（empty/None/duplicate ids）、_heading_boundary_ratio 边界（first-id matching + partial + duplicate headings）、_silent_drop_count 边界（empty expectations + sum across types + actuals 多于 expected）、_image_resource_ratio 边界（empty/zero-size/directory + image_base_dir lookup）、_text_preservation 边界（image filter + missing content + precision/recall 不对称）、compute_automatic_metrics keys 顺序精确、source_type='markdown' 边界、模块 namespace 完整性、helper metadata、不缓存行为

### 改动
- 新增 `tests/test_evaluation_metrics_edges15.py`（216 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码字符串 token**：13 个 helper def 全覆盖；含 'image_element_filter'/'silent_drop_formula'/'intersection_counter'/'chunk_first_id_assignment'/'image_base_dir_concat'/'isfile_check'/'st_size'/'heading_filter'/'image_filter'/'math_import'/'math_isfinite'/'pipeline_failed'/'no_elements'/'no_chunks'/'no_heading_elements'/'no_image_elements'/'no_expectations'/'pipeline_success_logic'/'pipeline_failed_loop'；不含 'print('
- **模块 docstring**：是 str 长度>100；含 'text_preservation'；含 '纯函数' 或 'Counter'
- **__all__ 类型与内容**：是 list 不是 tuple；只有 1 个元素 'compute_automatic_metrics'
- **namespace 完整性**：14 个函数全在 module namespace；Any identity；math/Counter 在 namespace；非 compute 的函数都 _ 前缀
- **常量精确**：_TEXT_TYPES 是 tuple 7 项；_PDF_BBOX_REQUIRED_TYPES 是 tuple 4 项；_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES；'image' 不在 _TEXT_TYPES；_NOT_EVALUATED='not_evaluated' 是 str
- **dict 字段名精确**：4 个 helper 返回 dict 都只有 'value'/'reason' 两 key；顺序 value→reason；可 JSON 序列化
- **签名 introspection**：compute_automatic_metrics 5 参数名精确；前 4 无默认，image_base_dir 默认 None；POSITIONAL_OR_KEYWORD；无 var args/kw；return_annotation 是 str（future annotations）
- **_strip_unicode_whitespace**：empty/no-ws/all-ws/pure-NBSP/mixed/中日韩/em space/en space/ideographic space/line sep/para sep/zero-width space（不删）；bytes/int/None raises
- **_is_valid_bbox**：None/[]/[1,2,3]/[1,2,3,4,5]/tuple/dict/set/string 拒绝；int/float/mixed 接受；True/False 拒绝；NaN/Inf/-Inf 拒绝；None/string in list 拒绝；返回类型 bool
- **_pdf_locator_ratio**：empty list → no_elements；page=0/-1/1.0/string 拒绝；page=1/True 接受；missing/None locator 拒绝；text-type 缺 bbox 拒绝；text-type + valid bbox 接受；partial=0.5
- **_docx_locator_ratio**：empty → no_elements；无 structural_keys 拒绝；section/paragraph_index/relationship_id 接受；page/bbox 拒绝；missing/None locator 拒绝；partial=0.5
- **_chunk_reference_ratio**：empty → no_chunks；empty/None/missing ids 视为空；all-valid → 1.0；duplicate ids 仍 valid
- **_heading_boundary_ratio**：empty/no-headings → no_heading_elements；no chunks → 0.0；first-id 匹配；非首位置不匹配；empty/None/missing ids 跳过；duplicate headings 全匹配
- **_silent_drop_count**：None/empty expectations → no_expectations；缺 element_count_by_type → no_expectations_element_count；empty element_count 同；no drop=0；drop N；actuals 多于 expected 不负；sum across types
- **_image_resource_ratio**：no images → no_image_elements；empty/None/missing rp → 0.0；existing+size>0 → 1.0；zero-size → 0.0；directory → 0.0；image_base_dir filename lookup；partial=0.5；OSError caught
- **_text_preservation**：empty empty → null+reason；equal=True；identical；image filtered；missing/None content 视为空；missing chunk text 视为空；precision<1 当 extra chars；recall<1 当 missing chars；empty expected + actual nonempty → empty_actual reason；nonempty expected + empty actual → empty_expected reason；ws-only 视为空
- **compute_automatic_metrics keys 顺序**：14 keys 精确顺序；error_code 取 error['code']；source_type='markdown' → not_pdf_document + not_docx_document；不抛错；不修改 error；每 metric 含 value+reason
- **helper metadata**：14 个函数 __qualname__/__module__ 精确
- **不缓存**：4 个 helper 各自返回独立 dict（修改一个不影响其他）

### 撞墙记录
- 0 fail：216 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 256 后）：22659 pass / 0 fail / 16 skip（HEAD `223cd30`）

### 下一步建议
- 候选 KW4：evaluation/report.py 第十六轮（200 行）
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW4（evaluation/report.py 第十六轮，200 行）继续推 evaluation。

---
## Round 257 — evaluation/report.py 第十六轮（147 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十六轮 edges 测试，覆盖未覆盖的源码 token（5 个 helper def + subprocess kwargs + importlib + datetime + version import + participating_docs/not_evaluated/macro_average/silent_drop_total + 不含 overall_score/combined_score/print）、模块 docstring 内容、模块 namespace 完整性、__all__ 类型与精确、常量精确（顺序敏感 + 三组互不相交 + 总和 14）、函数签名 introspection（每个函数参数名/默认/kind）、helper metadata（qualname/module）、aggregate_summary 详细计算（counts/success_rates/ratio_macro_averages/silent_drop_total 边界）、build_devset_section 用 stub Manifest 对象、build_provenance 字段类型验证 + run_timestamp_iso ISO parseable + max_chars int 转换、get_git_provenance 错误路径、get_dependency_versions 验证、cross-check 类型一致性

### 改动
- 新增 `tests/test_evaluation_report_edges16.py`（147 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：5 个 helper def 全覆盖；subprocess.run kwargs（capture_output/encoding/errors/timeout）；git status --porcelain；except OSError + subprocess.SubprocessError；import importlib.metadata；3 个包名 + PackageNotFoundError；datetime.now().astimezone().isoformat()；from evaluation import EVALUATOR_VERSION/REPORT_VERSION；participating_docs/not_evaluated/macro_average/silent_drop_total；不含 overall_score/combined_score/print；pypdfium2 注释
- **模块 docstring**：是 str 长度>30；含 '聚合' 或 'aggregat'；含 counts/success_rates/silent_drop
- **namespace 完整性**：3 个常量在 namespace；subprocess/datetime 是 identity；EVALUATOR_VERSION/REPORT_VERSION 值相等；__all__ 是 list 不是 tuple；5 个 entry 精确；所有名字在 namespace
- **常量精确**：3 个都是 tuple；_RATIO_METRICS 顺序精确 12 项；_COUNT_METRICS=['element_count_total']；_SUCCESS_BOOL_METRICS=['pipeline_success']；三组互不相交；总和 14；不含 figure_caption_*；不含 silent_drop_count/element_count_total
- **签名 introspection**：build_provenance 4 参数名精确 + 无默认 + POSITIONAL_OR_KEYWORD + 无 var args/kw + return str；build_devset_section 1 参数 + 无默认；aggregate_summary 1 参数；get_git_provenance 1 参数；get_dependency_versions 0 参数
- **helper metadata**：5 个函数 __qualname__/__module__ 精确；都是 FunctionType
- **aggregate_summary 4 keys 顺序**：counts → success_rates → ratio_macro_averages → silent_drop_total；空 per_doc 时各 sub-dict 结构精确
- **aggregate_summary 计算**：counts 求和 + 多 doc sum + null 不参与；success_rate 单 true/false/half + None value 不计入 success；ratio_macro_average simple/floats/None 排除；silent_drop_total 求和 + null 排除 + 全 None → None；缺 metric 视为 null；缺 'metrics' key 抛 KeyError；rate=None 当 per_doc 为空；不缓存
- **build_devset_section stub Manifest**：返回 dict；6 keys 精确顺序；pass-through 各字段；不修改 input；空 categories_covered
- **build_provenance**：返回 dict；9 keys 精确顺序；EVALUATOR_VERSION/REPORT_VERSION 值匹配；parser_name/version pass-through；max_chars int 转换（接受 str/int）；run_timestamp_iso ISO parseable；dependencies 3 包；git_commit str/None；git_dirty bool；不修改 input
- **get_git_provenance**：返回 dict 2 keys 顺序；值类型验证；处理不存在目录
- **get_dependency_versions**：返回 dict；3 keys；值是 str/None；pdfplumber 可解析（项目依赖）；无参数
- **__all__**：不含 helper 常量；含 5 helpers
- **cross-check**：aggregate_summary 后 ratio_macro_averages keys == _RATIO_METRICS；counts keys == _COUNT_METRICS；success_rates keys == _SUCCESS_BOOL_METRICS；not_evaluated = total - participating

### 撞墙记录
- 2 fail → 修复后 0 fail：
  - `test_aggregate_summary_handles_missing_metrics_key`：aggregate_summary 要求 per_doc 含 'metrics' key（不是 None-safe），改测期望 KeyError
  - `test_module_namespace_identity_evaluator_version`/`_report_version`：str 'is' 比较可能因 interning 不成立，改用 '==' 比较

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 257 后）：22806 pass / 0 fail / 16 skip（HEAD `0ef415a`）

### 下一步建议
- 候选 KX4：evaluation/cli.py 第十七轮（243 行）
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX4（evaluation/cli.py 第十七轮，243 行）继续推 evaluation。

---
## Round 258 — evaluation/cli.py 第十七轮（142 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十七轮 edges 测试，覆盖未覆盖的源码 token（5 个 import + add_subparsers/required=True/prog/description/RawDescriptionHelpFormatter + 3 个子命令名 + 4 个函数 def + if __name__/raise SystemExit + stdout/stderr reconfigure + utf-8/errors='replace' + 4 个 import 子句 + 3 个 args.command 分支 + return 2）、模块 docstring 内容、模块 namespace 完整性（argparse/json/sys/Path identity + 顶层 imports）、函数 metadata（4 个函数 module/qualname + 签名 introspection）、_build_parser 详细（3 subparser actions count + dests + choices + defaults + types + subparser required/dest/choices keys + prog/description/formatter_class）、_format_metric 边界（int/bool/None/dict 排序/empty dict/negative/large int/zero/no reason ok）、_run_inspect_doc 排序与缺字段（缺 source_type/elements/chunks/document_id/source_path/parser_name 各 fallback、None raises TypeError、tolerance_chars 透传）、main 函数错误路径（unknown command/no args/missing manifest/directory manifest/invalid JSON/validate-report 各路径）、模块顶层 reconfigure 行为

### 改动
- 新增 `tests/test_evaluation_cli_edges17.py`（142 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：4 个 import + 5 个 from-import + 4 个函数 def + 3 个子命令名 + prog/description/required/RawDescriptionHelpFormatter + args.command 三分支 + raise SystemExit + stdout/stderr reconfigure + utf-8/'replace' + if __name__ + return 2
- **模块 docstring**：是 str 长度>30；含 run/validate-report/inspect-doc；含 sanity check 或 单文档
- **namespace identity**：argparse/json/sys/Path 是 identity；main/_build_parser/_format_metric/_run_inspect_doc 在 namespace；load_manifest/ManifestError/EvalSchemaError/validate_file/run_evaluation/get_git_provenance 在 namespace；模块无 __all__
- **函数 metadata**：main argv 参数 default None + POSITIONAL_OR_KEYWORD + return 'int'；_build_parser 0 参数；_format_metric 2 参数 name+metric；_run_inspect_doc 1 参数 args；都 FunctionType；都无 var args/kw
- **_build_parser 详细**：返回 ArgumentParser；prog='evaluation.cli'；description 非空；formatter_class=RawDescriptionHelpFormatter；顶层 1 个 non-help action（command subparser）；subparser dest='command' + required=True + 3 个 choices keys；run subparser 5 args（manifest/output/parser/max_chars/tolerance_chars）+ parser choices=('fallback','kreuzberg') default 'fallback' + max_chars type int default 800 + tolerance_chars type int default 30；validate-report 1 个 positional arg；inspect-doc 2 个 args + tolerance_chars default 30
- **_format_metric 边界**：返回 str；含 name；float 4 位小数；int 直接渲染（不格式化为 .0000）；bool True/False 小写；None value 渲染 null+reason；dict value 渲染 items 并按 key 排序；empty dict 仍渲染 (ok)；string value 渲染；0/0.0 正确渲染（不视为 None）；无 reason 时 float/bool/dict/int/str 都用 'ok'；negative float 渲染；large int 渲染
- **_run_inspect_doc 缺字段**：缺 source_type → 用 'unknown'；缺 elements/chunks → 用 []; 缺 document_id/source_path/parser_name → 用 '?'；elements+chunks 数量正确；排序 bool 优先；tolerance_chars 透传；None elements → TypeError（已知未处理边界）；未知字段不抛错
- **main 错误路径**：unknown command/no args → SystemExit(2)；validate-report 文件不存在 → rc 2；非 JSON → rc 1；list JSON → rc 1；empty {} → rc 1；inspect-doc 文件不存在 → rc 2；非 JSON → rc 1；run manifest 不存在 → rc 2；manifest 是目录 → rc 2；manifest 非法 JSON → rc 1
- **整体一致性**：模块可 import；main 可调用；argparse/_SubParsersAction introspection

### 撞墙记录
- 2 fail → 修复后 0 fail：
  - `test_build_parser_run_subparser_actions_count`：run subparser 实际有 5 个 args（manifest/output/parser/max_chars/tolerance_chars）不是 4，改期望
  - `test_run_inspect_doc_handles_none_elements_field`：inspect-doc 不 None-safe（compute_automatic_metrics 在 len(None) 时抛 TypeError），改测期望 TypeError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 258 后）：22948 pass / 0 fail / 16 skip（HEAD `07e9cbf`）

### 下一步建议
- 候选 KS4：evaluation/runner.py 第十七轮（227 行）
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS4（evaluation/runner.py 第十七轮，227 行）继续推 evaluation。

---
## Round 259 — evaluation/runner.py 第十七轮（139 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十七轮 edges 测试，覆盖未覆盖的源码 token（5 个 import + 3 个函数 def + 5 个 from-import + _per_doc/parse_reason/chunk_reason/doc_id/source_type/metrics/wall_time_seconds/total/expected_failures/provenance/devset/summary/_annotation_present/_tolerance_chars/_missing_markers/image_dir/image_output_dir_for/write_json=False/unknown/mkdir(parents=True, exist_ok=True)/json.dump(ensure_ascii=False, indent=2)/except OSError + 不含 print）、模块 docstring 内容、模块 namespace 完整性（json/time/Path/Any/REPORT_VERSION identity + 7 个 imports）、模块 __all__ 精确（list 不是 tuple，1 个 entry 'run_evaluation'）、函数 metadata（3 个函数 module/qualname + 签名 introspection，run_evaluation keyword-only 标记精确：* separator 后 3 个 KEYWORD_ONLY）、_load_annotation 边界（None/不存在/目录/有效 JSON/无效 JSON/空文件/utf-8 BOM/str 路径 AttributeError）、run_evaluation 报告 6 top-level keys 顺序精确 + 各 sub-dict 结构验证、run_evaluation 不修改 manifest 的 documents/expected_failures/project_root、Stub Manifest 接口验证、kw-only 强制（positional 调用 raises TypeError）

### 改动
- 新增 `tests/test_evaluation_runner_edges17.py`（139 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：5 个 import（json/time/Path/Any/future annotations）+ 3 个函数 def + 5 个 from-import + 关键 token（_per_doc/parse_reason/chunk_reason/doc_id/source_type/metrics/wall_time_seconds/total/expected_failures/provenance/devset/summary/_annotation_present/_tolerance_chars/_missing_markers/image_dir/image_output_dir_for/write_json=False/unknown/mkdir(parents=True, exist_ok=True)/json.dump(ensure_ascii=False, indent=2)/except OSError）+ 不含 print
- **模块 docstring**：是 str 长度>30；含 total/pipeline/约束
- **namespace identity**：json/time/Path/Any identity；REPORT_VERSION 值匹配；process_single/image_output_dir_for/compute_automatic_metrics/chunk_boundary_prf/figure_caption_prf/aggregate_summary/build_devset_section/build_provenance 都在 namespace；不含 main
- **__all__**：是 list 不是 tuple；1 个 entry 'run_evaluation'；不含 helpers
- **函数 metadata**：_load_annotation 1 参数 path 无默认 + POSITIONAL_OR_KEYWORD + return str；_process_one 4 参数 + POSITIONAL_OR_KEYWORD + return str 含 'tuple'；run_evaluation 5 参数 + manifest/output_path POSITIONAL_OR_KEYWORD + parser_name/max_chars/tolerance_chars KEYWORD_ONLY + 默认 fallback/800/30 + return str；都 FunctionType；都无 var args/kw
- **_load_annotation 边界**：None/不存在/目录 → None；有效 JSON → dict；无效 JSON/空文件 → None；utf-8 BOM → None（encoding='utf-8' 不剥 BOM）；str 路径 → AttributeError（无 .is_file()）
- **run_evaluation report 6 keys 顺序**：report_version/provenance/devset/summary/per_doc/expected_failures；report_version 值匹配；各 sub-dict 是正确类型
- **summary 4 keys**：counts/success_rates/ratio_macro_averages/silent_drop_total；devset 6 keys；provenance 9 keys
- **provenance 字段值**：parser_name 默认 'fallback'；max_chars 默认 800；parser_version=None 当无 doc
- **写盘验证**：写 JSON 文件；含 report_version；provenance git_commit str/None；git_dirty bool；可覆盖；可创建嵌套目录
- **不修改 manifest**：documents/expected_failures/project_root identity 不变
- **kw-only 强制**：parser_name/max_chars/tolerance_chars 用 positional → TypeError
- **Stub Manifest**：categories_covered 可 list/tuple；devset_status 透传
- **空 manifest 不变量**：per_doc=[]/expected_failures=[]；summary silent_drop_total=None；success_rate total=0/rate=None

### 撞墙记录
- 39 fail → 修复后 0 fail：
  - `_make_empty_manifest` helper：class body 不能引用同名局部变量 `project_root`，改用 __init__ + closure
  - `test_load_annotation_param_default_none`：函数签名无 `=None`，default 是 `inspect.Parameter.empty` 不是 None

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 259 后）：23087 pass / 0 fail / 16 skip（HEAD `09db45e`）

### 下一步建议
- 候选 KZ4：evaluation/schema.py 第十轮（80 行）
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ4（evaluation/schema.py 第十轮，80 行）继续推 evaluation。

---
## Round 260 — evaluation/schema.py 第十轮（137 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第十轮 edges 测试，覆盖未覆盖的源码 token（5 个 import + 5 个 def/class + Draft202012Validator/iter_errors/sorted/absolute_path/absolute_schema_path/encoding='utf-8'/'Schema 文件不存在'/'校验失败'/'待校验文件不存在'/.resolve()/'不与 app/schema.py 复用' + 不含 print）、模块 docstring 内容、SCHEMAS_DIR 验证（Path 实例/absolute/is_dir/resolved/parent 是项目根/4 个 schema 文件存在）、EvalSchemaError 详细（is Exception/BaseException 子类 + MRO 长度 4 + __init__ 签名 + errors 默认 [] + args()/str()/repr()/hashable/可 raise/except/chained + equality by identity）、_schema_path（返回 Path/raises FileNotFoundError with path/absolute/unicode/spaces）、load_schema（不缓存每次新 dict/4 个 schema 都可加载/含 $schema key）、validate（成功返回 None/失败抛 EvalSchemaError/errors 是 list of dict/每 item 含 path/message/schema_path/排序按 absolute_path/message 含 schema_name + 错误数）、validate_file（接受 str+Path/各错误路径）、模块 namespace 完整性 + __all__ 精确、跨函数一致性

### 改动
- 新增 `tests/test_evaluation_schema_edges10.py`（137 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：5 个 import + 5 个 def/class + Draft202012Validator(schema)/iter_errors(instance)/sorted()/absolute_path/absolute_schema_path/encoding='utf-8'/'Schema 文件不存在'/'校验失败'/'待校验文件不存在'/.resolve()/'不与 app/schema.py 复用' + 不含 print
- **模块 docstring**：是 str 长度>10；含 manifest/annotation/evaluation-report；含 '不复用'/'不与'
- **SCHEMAS_DIR**：Path 实例；is_absolute；is_dir；resolved（无 .. 或 trailing .）；parent 是项目根含 pyproject.toml；4 个 schema 文件都在
- **EvalSchemaError**：是 Exception/BaseException 子类；MRO 4 items 含 BaseException；__init__ 3 参数 + errors 默认 None；errors=None → []；errors=[] → 替换为新 []；errors=truthy → keep reference；args=(message,)；str/repr/hashable；可 raise/except；可 raise from；equality by identity；errors 属性可写
- **_schema_path**：返回 Path + absolute；missing → FileNotFoundError with path in message；unicode/spaces name → FileNotFoundError
- **load_schema**：4 个 schema 都可加载；返回 dict；每次新 dict（不缓存）；含 $schema key；missing → FileNotFoundError
- **validate**：成功 None；失败 EvalSchemaError；errors 是 list of dict；每 item 含 path/message/schema_path；path/schema_path 是 list；message 是 str；message 含 schema_name + 错误数；按 absolute_path 排序
- **validate_file**：接受 str+Path；各错误路径（missing/directory/invalid JSON/invalid content）；signature 2 参数
- **namespace**：所有 5 个 export 在 namespace；json/Path/Draft202012Validator/JSValidationError identity；__all__ 是 list 不是 tuple；5 entries 精确；不含 _schema_path
- **跨函数**：validate 内部用 load_schema（missing schema → FileNotFoundError）；validate_file 内部用 validate（schema_name 透传）

### 撞墙记录
- 0 fail：137 测试一次性全过

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 260 后）：23224 pass / 0 fail / 16 skip（HEAD `4f9883c`）

### 下一步建议
- 候选 KT5：evaluation/manifest.py 第十七轮（239 行）
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT5（evaluation/manifest.py 第十七轮，239 行）继续推 evaluation。

---
## Round 261 — evaluation/manifest.py 第十七轮（197 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十七轮 edges 测试，覆盖未覆盖的源码 token（5 个 import + 5 个 class/def + 5 个 property + frozenset/seen/relative_to/resolve/encoding='utf-8'/validate 调用 + 错误 message token + 不含 print）、模块 docstring 内容（path 不变量/安全/绝对路径）、_is_absolute_like alpha check 详细（empty/single char/2 char/3 char/unicode alpha/non-alpha drive）、_has_backslash bool 类型、ManifestError 详细（is Exception/BaseException + MRO 4 + str/repr/args/hashable/equality by identity/不捕获其他 exception）、DocumentEntry/ExpectedFailure/Manifest dataclass 详细（is_dataclass + frozen=True + field count + field names in order + hashable + equality by value + module/qualname）、Manifest properties 详细（file_count/pdf_count/docx_count/categories_covered empty/single/multi/dedup/sorted/case-sensitive/unicode/new list each time、content_group_count 各种 pairing：no pair/one pair mutual/one-way/self-pair/pair-to-nonexistent/pair+unpaired）、_resolve_relative_path 详细（返回 Path/empty/absolute/backslash/outside root/subdir/unicode + 签名）、_detect_project_root 详细（find pyproject/no pyproject/file input/Path instance/absolute）、load_manifest 详细（接受 str path/project_root + 各错误路径 + 返回 Manifest/documents/expected_failures 是 tuple/project_root 是 Path + version mismatch raises EvalSchemaError）、模块 namespace 完整性 + __all__ 精确

### 改动
- 新增 `tests/test_evaluation_manifest_edges17.py`（197 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：5 个 import + 5 个 class/def + 5 个 property + frozenset/seen/relative_to(project_root_resolved)/.resolve()/encoding='utf-8'/validate(data, "manifest.schema.json") + 错误 message token（必须是相对路径/禁止反斜杠/禁止绝对路径/项目根目录之外/manifest_version 不兼容）+ 不含 print
- **模块 docstring**：是 str 长度>30；含 相对路径/正斜杠/项目根/绝对路径
- **_is_absolute_like**：empty=False；relative/single char/2 char=False；POSIX /foo=True；Windows C:\\foo / C:/foo=True；lower/upper drive=True；C:foo=False（无 separator）；non-alpha drive=False；unicode alpha=True；返回 bool 类型；FunctionType；签名 1 参数 path_str 无默认
- **_has_backslash**：empty/no backslash=False；with backslash/multiple/only backslash=True；返回 bool；FunctionType
- **ManifestError**：是 Exception/BaseException 子类；MRO 4 items 含 Exception + BaseException；可 raise/except；str/repr/args/hashable；equality by identity；不捕获 ValueError
- **DocumentEntry dataclass**：is_dataclass；frozen=True 阻止 setattr；10 fields 精确顺序；hashable；equality by value；module/qualname
- **ExpectedFailure dataclass**：is_dataclass；frozen=True；5 fields 精确顺序；hashable；module/qualname
- **Manifest dataclass**：is_dataclass；frozen=True；5 fields 精确顺序；hashable；module/qualname
- **Manifest properties**：file_count empty=0/one=1；pdf_count only pdf/mixed；docx_count only docx/zero when only pdf；categories_covered empty=[]/single/multi/dedup/sorted/case-sensitive/unicode/new list each call；content_group_count no pair=each 1 group/one mutual pair=1/one-way pair=1/self-pair=1/pair to nonexistent=1/pair+unpaired=2
- **_resolve_relative_path**：返回 absolute Path；empty raises with field_name；absolute raises 含 '绝对路径'；backslash raises 含 '反斜杠'；outside root raises 含 '项目根目录之外'；subdir OK；unicode filename OK；签名 3 参数全无默认；FunctionType
- **_detect_project_root**：找 pyproject.toml；无则返回 start；file input 取 parent；返回 Path + absolute；签名 1 参数；FunctionType
- **load_manifest**：签名 2 参数 manifest_path + project_root default None + POSITIONAL_OR_KEYWORD；missing/directory/invalid JSON/empty file 都 raises ManifestError；接受 str path/project_root；返回 Manifest 实例；documents/expected_failures 是 tuple；project_root 是 Path；pass-through manifest_version/devset_status；version mismatch raises EvalSchemaError（schema const 校验先失败）
- **namespace 完整性**：5 个 export 在 namespace；json/Path/MANIFEST_VERSION/validate identity；__all__ 是 list 不是 tuple；5 entries 精确；不含私有 helpers；所有 name 在 namespace
- **FunctionType**：5 个 helper 都是 FunctionType

### 撞墙记录
- 1 fail → 修复后 0 fail：
  - `test_load_manifest_version_mismatch_raises`：schema 中 manifest_version 是 const="1.0"，version "99.99" 先在 schema 失败抛 EvalSchemaError，改测期望 EvalSchemaError

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 261 后）：23421 pass / 0 fail / 16 skip（HEAD `95b5dfd`）

### 下一步建议
- 候选 KE5：evaluation/annotation_metrics.py 第十六轮（194 行）
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE5（evaluation/annotation_metrics.py 第十六轮，194 行）继续推 evaluation。

---
## Round 262 — evaluation/annotation_metrics.py 第十六轮（122 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十六轮 edges 测试，覆盖未覆盖的源码 token（5 个 import + 5 个 reason 字符串 + 3 个函数 def + tolerance_chars/search_from/missing_markers/predicted/normalize_text 调用/' '.join/stream.find/pairs.sort/used_pred+used_gt/f1 公式/denom<=0 检查 + 不含 print）、模块 docstring 内容（figure-caption/chunk boundary/一对一/容差/启发式）、函数签名 introspection（figure_caption_prf 2 参数无默认；chunk_boundary_prf 3 参数 tolerance_chars default 30 + POSITIONAL_OR_KEYWORD）、helper metadata、PARSER_DOES_NOT_EMIT_RELATIONS 详细（值/类型/hashable/singleton）、figure_caption_prf 详细（永远返回 null + reason；与输入无关）、chunk_boundary_prf 算法详细（document=None/None annotation/empty annotation/< 2 chunks/no anchors/perfect match/position before+after/tolerance exact/0/5/4 边界/2 chunks 2 anchors perfect/one-to-one no double counting/repeated markers sequential/missing markers recorded/empty marker treated as not found/position defaults/normalize chunk text/f1 when p or r None/f1 when both zero/f1 半匹配/tolerance record 结构/missing_markers 结构/不修改输入/不缓存）、模块 namespace 完整性 + __all__ 精确、与 evaluation.metrics 协作（_null/_ratio 调用一致）

### 改动
- 新增 `tests/test_annotation_metrics_edges16.py`（122 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：5 个 import + 5 个 reason 字符串（pipeline_failed/no_annotation/no_predicted_boundaries/no_ground_truth_anchors/no_ground_truth_anchors_in_stream/precision_or_recall_not_evaluated）+ 2 个 def + tolerance_chars: int = 30 + search_from/missing_markers/predicted/' '.join(norm_chunks)/stream.find/pairs.sort(key=lambda x: x[0])/used_pred+used_gt/2 * p_val * r_val / denom/if denom <= 0 + 不含 print
- **模块 docstring**：是 str 长度>30；含 figure-caption/chunk_boundary/一对一/容差/启发式/本期
- **签名 introspection**：figure_caption_prf 2 参数无默认 + POSITIONAL_OR_KEYWORD；chunk_boundary_prf 3 参数 + tolerance_chars default 30 + POSITIONAL_OR_KEYWORD（无 * separator）+ 无 var args/kw + return str
- **helper metadata**：2 个函数 __module__/__qualname__ 精确；FunctionType
- **PARSER_DOES_NOT_EMIT_RELATIONS**：值 'parser_does_not_emit_relations'；是 str；hashable；module singleton
- **figure_caption_prf**：返回 dict 3 keys；所有 value None + reason=PARSER_DOES_NOT_EMIT_RELATIONS；与输入无关（即使有 doc/annotation）；每 metric dict 含 value+reason
- **chunk_boundary_prf 算法**：document=None → pipeline_failed；None/empty annotation → no_annotation；< 2 chunks → no_predicted_boundaries + recall=0.0 当有 anchor；no anchors + 有 chunks → no_ground_truth_anchors；perfect match precision=recall=f1=1.0；position before vs after；tolerance_chars exact/0/5/4 边界；2 chunks 2 anchors perfect；一对一匹配 no double counting（precision=0.5 当 2 pred 1 gt）；repeated markers sequential search；missing markers 记录到 _missing_markers；empty marker → -1 → missing + recall null+reason；position defaults to 'after'；normalize chunk text 移除多余空白；f1 当 p/r None → precision_or_recall_not_evaluated；f1 当 both 0 → denom=0 → 0.0；f1 半匹配 (p=1/3, r=1) → 0.5；_tolerance_chars 总在输出；_missing_markers 仅在 missing 时
- **不修改输入**：document/annotation 不被修改
- **不缓存**：两次调用返回独立 dict
- **namespace 完整性**：Counter/Any/normalize_text/_null/_ratio/PARSER_DOES_NOT_EMIT_RELATIONS identity；2 个 export 在 namespace；__all__ 是 list 不是 tuple；3 entries 精确；不含私有
- **与 metrics 协作**：pipeline_failed 路径用 _null；perfect match 路径用 _ratio

### 撞墙记录
- 1 fail → 修复后 0 fail：
  - `test_chunk_boundary_prf_empty_marker_treated_as_not_found`：empty marker → gt=[] → recall null + reason 'no_ground_truth_anchors_in_stream'，不是 0.0；改测期望 None + reason

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 262 后）：23543 pass / 0 fail / 16 skip（HEAD `9c0d49d`）

### 下一步建议
- 候选 KF5：evaluation/metrics.py 第十六轮（381 行）
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF5（evaluation/metrics.py 第十六轮，381 行）继续推 evaluation。

---

## Round 263 — evaluation/metrics.py 第十六轮（141 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十六轮 edges 测试，进一步覆盖未覆盖的源码 token（14 个 def + 7 个 type tokens + 7 个 docx structural keys + pipeline logic + error messages + counter intersection + chunk_first_ids.add + silent_drop formula + image filter + heading filter + image_resource_path_check + image_size_check + image_isfile_check + except OSError + no print）、模块 docstring 内容（pure function/no mutation/text_preservation/v1.1/Counter/Unicode/image excluded）、函数签名 introspection（14 functions）、helper metadata、constants namespace 完整性、_is_valid_bbox 各 PDF required type、_pdf_locator_ratio 每 text type、_docx_locator_ratio 每 structural key、_image_resource_ratio（image_base_dir filename lookup）、_chunk_reference_ratio（missing/None element_id）、_heading_boundary_ratio（duplicate first id, missing element_id）、_silent_drop_count multiple expected types、_text_preservation（unicode/emoji/control chars/surrogate pairs/ZWJ/precision-recall asymmetry/repeated chars/all image elements/empty chunks）、compute_automatic_metrics（docx/pdf source_type paths, error_code pass-through, no mutation, no shared state, 14 keys consistent）、namespace identity、helper no-caching

### 改动
- 新增 `tests/test_evaluation_metrics_edges16.py`（141 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **源码 token**：14 个 def token + 7 个 type tokens（list[dict]/dict[str, Any]/int/Path | None/str/bool/set）+ 7 个 docx structural keys（paragraph_index/row_index/table_index/list_level/run_index）+ pipeline logic + error messages + counter intersection + chunk_first_ids.add + silent_drop formula + image filter + heading filter + image_resource_path_check + image_size_check + image_isfile_check + except OSError + 不含 print
- **模块 docstring**：是 str 长度>30；含 pure function/no mutation/text_preservation/v1.1/Counter/Unicode/image excluded
- **签名 introspection**：14 个函数（_null/_ratio/_is_valid_bbox/_pdf_locator_ratio/_docx_locator_ratio/_image_resource_ratio/_chunk_reference_ratio/_heading_boundary_ratio/_silent_drop_count/_text_preservation/compute_automatic_metrics + 2 helpers + EvaluatorVersion）；参数计数、默认值（None / inspect.Parameter.empty）、POSITIONAL_OR_KEYWORD、无 var args/kw
- **helper metadata**：14 个 helper __module__/__qualname__ 精确；FunctionType
- **常量 namespace**：_TEXT_TYPES 7 项精确（heading/paragraph/table/list/header/footer/image）；_PDF_BBOX_REQUIRED_TYPES 4 项精确（heading/paragraph/table/list）；_NOT_EVALUATED 完整；subset 关系；image 不在 evaluated 类型
- **_is_valid_bbox**：各 PDF required type 走查（heading/paragraph/table/list 都需要 bbox）；非 required type 不调用
- **_pdf_locator_ratio**：各 text type（heading/paragraph/table/list 需 bbox；header/footer 不需 bbox）
- **_docx_locator_ratio**：各 structural key（paragraph_index/row_index/table_index/list_level/run_index）
- **_image_resource_ratio**：image_base_dir filename lookup（绝对路径优先、image_base_dir 兜底）；rp 含 basename 提取
- **_chunk_reference_ratio**：missing element_id（不计入 denominator）；None element_id（不计入 denominator）
- **_heading_boundary_ratio**：duplicate first id（只计一次）；missing element_id（不计）
- **_silent_drop_count**：多 expected types 之和；0 expected → 0
- **_text_preservation**：unicode/emoji/control chars/surrogate pairs/ZWJ 精度召回不对称（norm 等价但 raw 不等价）/repeated chars/all image elements（分母 0）/empty chunks（chunks=[]→null+reason）
- **compute_automatic_metrics**：docx source_type 路径；pdf source_type 路径；error_code pass-through；不修改 elements；无共享状态；14 keys 一致（counts/locator_prf 等）
- **namespace identity**：math/Counter/Path/Any 模块属性 identity
- **helper no-caching**：两次调用返回独立 dict

### 撞墙记录
- 1 fail → 修复后 0 fail：
  - `test_image_resource_ratio_image_base_dir_default_none`：`_image_resource_ratio` 的 `image_base_dir` 无默认值（`inspect.Parameter.empty`，不是 None）；改名 `test_image_resource_ratio_image_base_dir_no_default` 并改断言

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 263 后）：23684 pass / 0 fail / 16 skip（HEAD `9df9b80`）

### 下一步建议
- 候选 KW5：evaluation/report.py 第十七轮（200 行）
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW5（evaluation/report.py 第十七轮，200 行）继续推 evaluation。

---

## Round 264 — evaluation/report.py 第十七轮（96 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十七轮 edges 测试，覆盖 edges16 未触及的角度：所有 ratio metric 走查（不只 schema_valid）、schema_valid boolean-as-ratio 混合、text_preservation_equal 浮点、chunk_boundary_f1 三种 None/0/0.5、not_evaluated + participating = total、success_count + failure = total、单 doc 全 None、多 doc 同 metric 全 null、metrics 缺失某 metric、空 metrics dict、per_doc 异常（None/int/str/dict-with-non-dict-metric）、build_provenance max_chars=0/-1/布尔、run_timestamp_iso 带 tz offset、parser_name 空串、dependencies 值类型、两次调用独立 dict、build_devset_section 边界（empty status/huge file_count/pdf+docx≠file_count/categories identity）、get_git_provenance 真实跑/异常路径（FileNotFoundError → commit None + dirty True）、get_dependency_versions 异常路径（Exception / PackageNotFoundError）、__all__ 不含 EVALUATOR_VERSION/REPORT_VERSION/subprocess/datetime/Path/Any、_RATIO_METRICS 含 schema_valid/chunk_boundary 三联/text_char_multiset 双联、不含 element_count_total/pipeline_success、源码 token 含 _COUNT_METRICS 循环/_SUCCESS_BOOL_METRICS 循环/_RATIO_METRICS 循环/int(max_chars)/不含 json/os/asyncio/threading/logging、aggregate_summary counts/success_rates/ratio_macro_averages 各自只含对应 metric set、silent_drop_total top-level 不混入子 dict

### 改动
- 新增 `tests/test_evaluation_report_edges17.py`（96 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **aggregate_summary 深度**：所有 13 个 ratio metric 走查（不只 schema_valid）；schema_valid boolean-as-ratio 混合 True/False/None；text_preservation_equal 浮点混合；chunk_boundary_f1 zero/half/all-none；not_evaluated + participating = total；success_count + (total - success_count) = total；rate=None 当 total=0
- **aggregate_summary 边界**：单 doc 全 None → 每个 ratio macro_average None + participating 0 + not_evaluated 1；多 doc 同 metric 全 null；某 metric 仅部分 doc 提供；空 metrics dict per_doc；missing 'metrics' key（KeyError）；missing metrics value（TypeError）；per_doc is None（TypeError）；per_doc 是 str（TypeError）；metric value 不是 dict（AttributeError）
- **build_provenance 深度**：max_chars=0/-1/True/False 都 int() 转换；run_timestamp_iso 带时区偏移；run_timestamp_iso 解析回 datetime；parser_name 空串；dependencies 三 package 值类型；两次调用独立 dict；evaluator/report_version 都是 str
- **build_devset_section 深度**：empty status；huge file_count；pdf+docx≠file_count（不强制一致）；categories identity 保留；两次调用独立 dict；调用过程不修改 manifest 属性
- **get_git_provenance 深度**：真实项目根目录返回 40-char hex git_commit；tmp_path 不是 git repo → commit None 或 str、dirty 是 bool；两次调用独立 dict；subprocess.run 至少调 1 次（监控）；FileNotFoundError 异常 → catch → commit None + dirty True
- **get_dependency_versions 深度**：pypdfium2/python-docx 值类型；两次调用独立但 value 一致；Exception → catch → None；PackageNotFoundError → catch → None
- **模块 namespace 完整性**：__all__ 不含 EVALUATOR_VERSION/REPORT_VERSION/subprocess/datetime/Path/Any；namespace 有 EVALUATOR_VERSION/REPORT_VERSION/Path/Any；_RATIO_METRICS 含 schema_valid/chunk_boundary 三联/text_char_multiset 双联；_COUNT_METRICS 不含 silent_drop_count；_SUCCESS_BOOL_METRICS 不含 schema_valid
- **源码 token**：含 for name in _COUNT_METRICS/_SUCCESS_BOOL_METRICS/_RATIO_METRICS 循环、silent_drop_count、pipeline_success、element_count_total、success_count、rate、int(max_chars)；不含 json/os/asyncio/threading/logging
- **aggregate_summary 不混合类型**：counts 只含 _COUNT_METRICS；success_rates 只含 _SUCCESS_BOOL_METRICS；ratio_macro_averages 只含 _RATIO_METRICS；silent_drop_total 是 top-level key，不在任何子 dict

### 撞墙记录
- 4 fail → 修复后 0 fail：
  - `test_aggregate_summary_per_doc_is_none_raises_type_error`：None[X] 抛 TypeError 不是 AttributeError；改 TypeError
  - `test_aggregate_summary_per_doc_not_dict_raises_attribute_error`：'str'['metrics'] 抛 TypeError 不是 AttributeError；改 TypeError
  - `test_build_devset_section_does_not_mutate_categories_input`：build_devset_section 直接引用 manifest.categories_covered 到输出 dict，修改输出会修改输入；改为只验证调用过程不修改 manifest 属性
  - `test_get_git_provenance_in_tmp_path_dirty_is_true`：tmp_path 不是 git repo，git status --porcelain 返回非零，dirty = bool(False and ...) = False；改为断言 dirty 是 bool

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 264 后）：23780 pass / 0 fail / 16 skip（HEAD `c58f072`）

### 下一步建议
- 候选 KX5：evaluation/cli.py 第十八轮（243 行）
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX5（evaluation/cli.py 第十八轮，243 行）继续推 evaluation。

---

## Round 265 — evaluation/cli.py 第十八轮（133 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：_build_parser 详细（prog/description/formatter_class/subparsers required/dest/choices/run 5 args/validate 1 arg/inspect 2 args/required raises SystemExit/parser choices/default/max-chars type int/tolerance-chars default 30）、_format_metric 每个分支（None/bool True/bool False/bool + reason None→ok/bool + explicit reason/float 4 位小数/int default 分支/int zero/negative int/dict sorted items/empty dict/str default/list default/missing value key/missing reason key/empty dict/name alignment 36）、_run_inspect_doc 详细（input 不存在/invalid JSON/top not dict/top string/minimal dict/missing source_type default unknown/missing elements/missing chunks/elements+chunks 计数/file line/document_id line/source line/parser line/metrics line 顺序/sort bool first/tolerance_chars 透传/default 30/returns 0）、main inspect-doc 路径（not a file/invalid json/list top/tolerance-chars arg）、main validate-report 路径（not a file/invalid json/list top）、main run 错误路径（manifest not file/manifest is directory）、模块源码 token 含 import 详细（runner/manifest/schema/report）/subparsers required=True/RawDescriptionHelpFormatter/max-chars 800/tolerance-chars 30×2/reconfigure stdout+stderr/hasattr/AttributeError+OSError/4 个 def/__name__ == __main__/不含 os/subprocess/logging/asyncio、namespace has argparse/json/sys/Path/main/build_parser/format_metric/run_inspect_doc（callable + FunctionType）、helper metadata（4 个 __module__/__qualname__）、签名 introspection（main 1 参数 argv default None POSITIONAL_OR_KEYWORD；_build_parser 0 参数；_format_metric 2 参数 name+metric 无默认；_run_inspect_doc 1 参数 args 无默认）

### 改动
- 新增 `tests/test_evaluation_cli_edges18.py`（133 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_build_parser 详细**：prog='evaluation.cli'；description 含 '评测'；formatter_class 是 RawDescriptionHelpFormatter；subparsers required=True；dest='command'；3 子命令 run/validate-report/inspect-doc；run 5 个 user action（manifest/output/parser/max_chars/tolerance_chars）；validate 1 个（input）；inspect 2 个（input/tolerance_chars）；required 参数缺 → SystemExit；--parser default fallback；choices ('fallback', 'kreuzberg')；invalid choice → SystemExit；--max-chars default 800 + type=int；invalid type → SystemExit；--tolerance-chars default 30；inspect-doc default 30；input positional；command dest；no command → SystemExit；unknown command → SystemExit
- **_format_metric 详细**：None value → 'null'；bool True/False → 'true'/'false'；bool + reason None → '(ok)'；bool + explicit reason → '(custom)'；float → 4 位小数（0.123456789 → 0.1235）；float 0.0/1.0；int default 分支；int 0；negative int；dict sorted items（a=1 < b=2 < c=3 顺序）；empty dict；str default；list default；missing value key → null；missing reason key → (None)；empty dict → null；name alignment 36 chars（'  {name:36} null  (x)'）
- **_run_inspect_doc 详细**：input 不存在 → 2；invalid JSON → 1；top 是 list → 1；top 是 string → 1；minimal dict 返回 0；缺 source_type → 'unknown'；缺 elements → 'elements=0'；缺 chunks → 'chunks=0'；elements=None → TypeError（compute_automatic_metrics 不 None-safe）；有 elements+chunks → 计数正确；输出含 file/document_id/source/parser/counts/metrics 行；metrics 在 counts 之后；bool value 排第一；tolerance_chars 透传；default 30；return 0
- **main inspect-doc 路径**：not file → 2；invalid JSON → 1；list top → 1；带 --tolerance-chars arg → 0
- **main validate-report 路径**：not file → 2；invalid JSON → 1；list top → 1
- **main run 错误路径**：manifest not file → 2；manifest is directory → 2
- **模块源码 token**：含 from evaluation.runner import run_evaluation / from evaluation.manifest import / load_manifest / ManifestError / from evaluation.schema import / validate_file / EvalSchemaError / from evaluation.report import / get_git_provenance / required=True / RawDescriptionHelpFormatter / default=800 / default=30 (≥2 次) / sys.stdout.reconfigure / sys.stderr.reconfigure / hasattr(sys.stdout, "reconfigure") / AttributeError / OSError / def main / def _build_parser / def _run_inspect_doc / def _format_metric / if __name__ == "__main__" / SystemExit(main())；不含 import os / import subprocess / import logging / asyncio；含 import json / import sys / from pathlib import Path
- **namespace identity**：hasattr argparse/json/sys/Path/main/_build_parser/_format_metric/_run_inspect_doc；callable + FunctionType（避免 reload 后 is 失败）
- **helper metadata**：4 个 __module__ == 'evaluation.cli'；4 个 __qualname__（main/_build_parser/_format_metric/_run_inspect_doc）
- **签名 introspection**：main 1 参数 argv default None POSITIONAL_OR_KEYWORD；无 var args/kw；_build_parser 0 参数；_format_metric 2 参数 name+metric 无默认；_run_inspect_doc 1 参数 args 无默认

### 撞墙记录
- 2 fail（孤立跑）→ 修复后 0 fail：
  - `test_format_metric_name_alignment_36_chars`：name 占 36 char，但我算错了字符数（34 padding + 1 literal space = 35，不是 34）；改 35
  - `test_run_inspect_doc_elements_null_treated_as_empty`：compute_automatic_metrics 直接读 doc['elements']，不 None-safe；改为 expect TypeError
- 4 fail（全量回归）→ 修复后 0 fail：
  - `test_module_namespace_has_main`/`_build_parser`/`_format_metric`/`_run_inspect_doc`：其他测试（test_evaluation_cli_edges.py / test_evaluation_cli_edges17.py）调 importlib.reload(evaluation.cli)，reload 后 module 内函数是新对象，与测试文件顶部导入的旧引用 is 不相等；改为 callable + FunctionType 检查，不做 is 比较

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 265 后）：23913 pass / 0 fail / 16 skip（HEAD `ae48e8d`）

### 下一步建议
- 候选 KS5：evaluation/runner.py 第十八轮（227 行）
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS5（evaluation/runner.py 第十八轮，227 行）继续推 evaluation。

---

## Round 266 — evaluation/runner.py 第十八轮（118 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：_load_annotation 详细（Path 对象/None/不存在/空文件/invalid JSON/list 顶层/string 顶层/dict 顶层/BOM 头→None/二进制垃圾→UnicodeDecodeError/返回类型）、_process_one 签名（4 参数 doc/output_root/parser_name/max_chars 无默认 POSITIONAL_OR_KEYWORD，return annotation 是 tuple）、run_evaluation 签名（5 参数 manifest/output_path 无默认 POSITIONAL_OR_KEYWORD + parser_name/max_chars/tolerance_chars KEYWORD_ONLY 默认 fallback/800/30）、helper metadata（3 个 __module__/__qualname__）、模块 namespace（json/time/Path/Any/REPORT_VERSION/process_single/image_output_dir_for/compute_automatic_metrics/chunk_boundary_prf/figure_caption_prf/aggregate_summary/build_devset_section/build_provenance）、__all__ 单元素 ['run_evaluation']、源码 token 含 perf_counter/not_instrumented/write_json=False/image_output_dir_for/_per_doc/out_stub.unlink/except OSError/expected_failures loop/documents loop/public_per_doc/_annotation_present/_tolerance_chars pop/_missing_markers pop/json.dump/ensure_ascii=False/indent=2/不含 print/logging/asyncio/subprocess/os/concurrent.futures/含 unknown/process_single returned None 消息、docstring 含 perf_counter/not_instrumented/pipeline_failed/image_resource_exists_ratio/image_output_dir/write_json=False、EmptyManifest smoke test（report 6 top keys/per_doc empty list/expected_failures empty list/report_version/summary 4 keys/provenance 9 keys/devset 6 keys/写盘 valid JSON/两次调用独立/不修改 manifest documents+expected_failures+project_root/创建 output dir/parser_name/max_chars default/kreuzberg parser/custom max_chars/custom tolerance_chars/空 manifest 不创建 _per_doc subdir）

### 改动
- 新增 `tests/test_evaluation_runner_edges18.py`（118 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation 详细**：None → None；不存在 → None；空文件 → None；invalid JSON → None；list 顶层 → 返回 list；string 顶层 → 返回 string；dict 顶层 → 返回 dict；BOM 头 → json 抛 JSONDecodeError → None；二进制 0xff → UnicodeDecodeError（不在 except 中）；签名 1 参数 path 无默认 POSITIONAL_OR_KEYWORD；无 var args/kw
- **_process_one 签名**：4 参数 doc/output_root/parser_name/max_chars；无默认；POSITIONAL_OR_KEYWORD；无 var args/kw；return annotation 是 str 形式的 tuple
- **run_evaluation 签名**：5 参数 manifest/output_path（POSITIONAL_OR_KEYWORD 无默认）+ parser_name/max_chars/tolerance_chars（KEYWORD_ONLY 默认 'fallback'/800/30）；无 var args/kw；return annotation str
- **helper metadata**：3 个 helper __module__ == 'evaluation.runner'；__qualname__ 精确；FunctionType
- **namespace 完整性**：json/time/Path/Any/REPORT_VERSION/process_single/image_output_dir_for/compute_automatic_metrics/chunk_boundary_prf/figure_caption_prf/aggregate_summary/build_devset_section/build_provenance 都在；__all__ 是 list 不是 tuple；__all__ == ['run_evaluation']；__all__ 不含 _load_annotation/_process_one/REPORT_VERSION/process_single/image_output_dir_for
- **源码 token**：含 from __future__ import annotations、import time、perf_counter、"not_instrumented"（双引号）、write_json=False、image_output_dir_for(、image_base_dir=、_per_doc、out_stub.unlink、except OSError、for ef in manifest.expected_failures、for doc in manifest.documents、public_per_doc、_annotation_present、_tolerance_chars、_missing_markers、json.dump(report, f、ensure_ascii=False、indent=2、"unknown"、"process_single returned None without errors"；不含 print/import logging/asyncio/import subprocess/import os/concurrent.futures/ThreadPoolExecutor/ProcessPoolExecutor
- **docstring 内容**：是 str 长度>30；含 runner 或 评测；含 perf_counter；含 not_instrumented；含 pipeline_failed；含 image_resource_exists_ratio；含 image_output_dir；含 write_json=False
- **EmptyManifest smoke test**：空 manifest 跑通；report 6 top keys 精确；per_doc=[]；expected_failures=[]；report_version=REPORT_VERSION；summary 4 keys；provenance 9 keys；devset 6 keys；写盘 JSON 可重新解析；两次调用独立 dict；不修改 manifest documents/expected_failures/project_root；output 父目录自动创建；parser_name 默认 'fallback'；max_chars 默认 800；custom parser_name/kreuzberg；custom max_chars；custom tolerance_chars；空 manifest 不创建 _per_doc subdir

### 撞墙记录
- 4 fail → 修复后 0 fail：
  - `test_load_annotation_utf8_bom_tolerated`：json.load 不容忍 BOM，BOM 解码后是 ﻿ 字符让 JSON 抛 JSONDecodeError → catch → None；改为期望 None
  - `test_load_annotation_binary_garbage_returns_none`：二进制 0xff → UnicodeDecodeError（ValueError 子类）不在 except (OSError, json.JSONDecodeError) 中；改为 expect UnicodeDecodeError
  - `test_module_source_contains_not_instrumented_reason`：源码只用双引号 "not_instrumented"，不含单引号形式；移除单引号断言
  - `test_run_evaluation_creates_per_doc_subdir`：空 manifest → for doc in manifest.documents 循环不执行 → _per_doc 不创建；改为 not exists 或 is_dir 的弱断言

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 266 后）：24031 pass / 0 fail / 16 skip（HEAD `af0b19d`）

### 下一步建议
- 候选 KZ5：evaluation/schema.py 第十一轮（80 行）
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ5（evaluation/schema.py 第十一轮，80 行）继续推 evaluation。

---

## Round 267 — evaluation/schema.py 第十一轮（134 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第十一轮 edges 测试，覆盖 edges10 未触及的角度：EvalSchemaError __init__ 详细（self/message/errors 3 参数；errors default None；message no default；POSITIONAL_OR_KEYWORD；no var_kwargs；errors=None → []；errors=[] → []；errors=list 透传 identity；errors=non-list 透传；str/repr/args；raise/except；mro；__module__/__qualname__；has errors/args attr）、_schema_path 详细（返回 Path/absolute/resolved/existing file/3 个已知 schema 都加载；不存在 → FileNotFoundError 含路径；签名 1 参数 name 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；__module__/__qualname__）、load_schema 详细（返回 dict；两次调用不同 dict 不缓存；3 个已知 schema 都返回 dict；不存在 → FileNotFoundError；签名 1 参数 name 无默认）、validate 详细（签名 2 参数 instance+schema_name 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；return None 或 'None'；valid manifest → return None；invalid → EvalSchemaError；error message 含 schema_name + count + path=；errors attribute 是 list；每个 error 有 path/message/schema_path 都是 list/str/list；sorted by absolute_path；__module__/__qualname__）、validate_file 详细（签名 2 参数 path+schema_name 无默认；接受 str 和 Path；不存在 → FileNotFoundError；invalid JSON → JSONDecodeError；schema 校验失败 → EvalSchemaError；error message 含 path；__module__/__qualname__）、SCHEMAS_DIR 详细（Path 实例/absolute/is_dir/含 3 个已知 schema；parent 是 project root 含 pyproject.toml；name=='schemas'）、namespace 完整性（json/Path/Any/Draft202012Validator/JSValidationError/SCHEMAS_DIR/EvalSchemaError/load_schema/validate/validate_file/_schema_path；__all__ 是 list 不是 tuple；__all__ == 5 entries；__all__ 不含 _schema_path/json/Path/Any/Draft202012Validator/JSValidationError）、源码 token（含 from __future__ import annotations/import json/from pathlib import Path/from typing import Any/from jsonschema import Draft202012Validator/from jsonschema.exceptions import ValidationError as JSValidationError/SCHEMAS_DIR = Path(__file__).resolve().parent.parent / 'schemas'/class EvalSchemaError/super().__init__(message)/self.errors = errors or []/sorted(validator.iter_errors/absolute_path/absolute_schema_path/err.message/head = errors[0]；不含 print/import logging/@lru_cache/functools.cache/asyncio/import subprocess/import os）、docstring 内容（是 str 长度>30；含 manifest/annotation/evaluation-report；含 app/schema.py 或 复用；含 业务 或 评测）

### 改动
- 新增 `tests/test_evaluation_schema_edges11.py`（134 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **EvalSchemaError 详细**：__init__ 3 参数 self/message/errors；errors default None；message no default；POSITIONAL_OR_KEYWORD；no var_kwargs；无 args → errors=[]；explicit None → []；explicit []→[]；explicit list 透传 identity；explicit non-list 透传（不强制类型）；str 含 message；repr 含 class name；args == (message,)；raise/catch；mro 含 Exception+BaseException；__module__/__qualname__；has errors+args attr
- **_schema_path 详细**：返回 Path 对象；is_absolute；resolve() 已应用；is_file；3 个已知 schema（manifest/annotation/evaluation-report）都可加载；不存在 → FileNotFoundError 含完整路径；签名 1 参数 name 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；__module__/__qualname__
- **load_schema 详细**：返回 dict；两次调用返回不同 dict（不缓存）；3 个已知 schema 都返回 dict；不存在 → FileNotFoundError；签名 1 参数 name 无默认；__module__/__qualname__
- **validate 详细**：签名 2 参数 instance+schema_name 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；return annotation None 或 'None'；valid manifest instance → return None；invalid → EvalSchemaError；error message 含 schema_name + 处/count + path=；errors attribute 是 list；每个 error 有 path（list）/message（str）/schema_path（list）；sorted by absolute_path（验证 paths == sorted(paths)）；__module__/__qualname__
- **validate_file 详细**：签名 2 参数 path+schema_name 无默认；接受 str 和 Path 对象；不存在 → FileNotFoundError；invalid JSON → JSONDecodeError；schema 校验失败 → EvalSchemaError；error message 含 path；__module__/__qualname__
- **SCHEMAS_DIR 详细**：Path 实例；is_absolute；is_dir；含 3 个已知 schema 文件；parent 是 project root（含 pyproject.toml）；name == 'schemas'
- **namespace 完整性**：json/Path/Any/Draft202012Validator/JSValidationError/SCHEMAS_DIR/EvalSchemaError/load_schema/validate/validate_file/_schema_path 都在 namespace；__all__ 是 list 不是 tuple；5 entries 精确；__all__ 不含 _schema_path/json/Path/Any/Draft202012Validator/JSValidationError
- **源码 token**：含 from __future__ import annotations、import json、from pathlib import Path、from typing import Any、from jsonschema import Draft202012Validator、from jsonschema.exceptions import ValidationError as JSValidationError、SCHEMAS_DIR 定义（Path(__file__).resolve().parent.parent / 'schemas'）、class EvalSchemaError、super().__init__(message)、self.errors = errors or []、sorted(validator.iter_errors、absolute_path、absolute_schema_path、err.message、head = errors[0]；不含 print/import logging/@lru_cache/functools.cache/asyncio/import subprocess/import os
- **docstring 内容**：是 str 长度>30；含 manifest/annotation/evaluation-report；含 app/schema.py 或 复用；含 业务 或 评测

### 撞墙记录
- 3 fail → 修复后 0 fail：
  - `test_validate_valid_manifest_returns_none`：测试 instance 含 devset 嵌套字段，但 schema 实际是顶层 devset_status + additionalProperties:false → 校验失败；改为顶层 devset_status 字段
  - `test_validate_file_path_str_accepted`/`test_validate_file_path_pathlib_accepted`：同样问题，devset 嵌套字段不被 schema 接受；改为顶层 devset_status 字段

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 267 后）：24165 pass / 0 fail / 16 skip（HEAD `49abd51`）

### 下一步建议
- 候选 KT6：evaluation/manifest.py 第十八轮（239 行）
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT6（evaluation/manifest.py 第十八轮，239 行）继续推 evaluation。

---

## Round 268 — evaluation/manifest.py 第十八轮（170 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：_is_absolute_like 边界更多（空/'a'/'ab'/'a:'/'a:b'/'a:\\b'/'a:/b'/'1:\\b'/'C:/x'/'c:/x'/'/foo'/'/'/'a/b'/'./foo'/'../foo'/返回 bool）、_has_backslash 边界（空/单 backslash/多 backslash/forward only/mixed/no/返回 bool）、_resolve_relative_path（成功路径返回 Path/空 path 抛错含字段名/POSIX 绝对/Windows drive/backslash/outside root/签名 3 参数/POSITIONAL_OR_KEYWORD/__module__/__qualname__）、_detect_project_root（start 是目录/start 是文件在 root/start 是文件在 subdir/无 pyproject 返回 cur/返回 Path/签名 1 参数）、ManifestError（is Exception/BaseException subclass/mro/__module__/__qualname__/str/args/repr/raise/无 errors attr）、DocumentEntry frozen（setattr 抛 FrozenInstanceError/delattr/is_dataclass/10 fields/字段名顺序/frozen=True/__module__/__qualname__）、ExpectedFailure frozen（同上/5 fields）、Manifest frozen（同上/5 fields）、Manifest property（file_count/pdf_count/docx_count/content_group_count 各种 pairing/categories_covered 去重排序/返回 list 不是 tuple/每次返回新 list）、namespace 完整性（json/dataclass/Path/Any/MANIFEST_VERSION/validate/ManifestError/DocumentEntry/ExpectedFailure/Manifest/load_manifest/_is_absolute_like/_has_backslash/_resolve_relative_path/_detect_project_root；__all__ 是 list 不是 tuple；5 entries；不含私有 helpers/constants）、源码 token（含 from __future__ import annotations/import json/from dataclasses import dataclass/from pathlib import Path/from typing import Any/from evaluation import MANIFEST_VERSION/from evaluation.schema import validate/class ManifestError/@dataclass(frozen=True)/class DocumentEntry/ExpectedFailure/Manifest/@property/manifest_version+MANIFEST_VERSION/relative_to/frozenset；不含 print/import logging/import subprocess/import os/asyncio/abspath/realpath/.read_text(）、docstring（含 相对路径/绝对路径/反斜杠/项目根/本机）

### 改动
- 新增 `tests/test_evaluation_manifest_edges18.py`（170 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_is_absolute_like 边界**：空 → False；'a' → False（len<3）；'ab' → False；'a:' → False（len<3）；'a:b' → False（path_str[2] 不在 \\/）；'a:\\b' → True（盘符+backslash）；'a:/b' → True（盘符+slash）；'1:\\b' → False（数字开头）；'C:/x' → True（大写盘符）；'c:/x' → True（小写盘符）；'/foo' → True（POSIX）；'/' → True；'a/b' → False；'./foo' → False；'../foo' → False；返回 bool
- **_has_backslash 边界**：空 → False；'\\' → True；'a\\b\\c' → True；'a/b/c' → False；'a/b\\c' → True；'foo' → False；返回 bool
- **_resolve_relative_path**：成功返回 resolved absolute Path；空 path → ManifestError 含字段名+为空；POSIX 绝对 → ManifestError 含字段名+绝对路径；Windows drive → ManifestError；backslash → ManifestError 含字段名+反斜杠；../etc → ManifestError 含字段名+项目根目录之外；签名 3 参数 path_str/project_root/field_name 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；__module__/__qualname__
- **_detect_project_root**：start 是目录且含 pyproject.toml → 返回该目录；start 是文件 → 取 parent；start 是子目录中文件 → 向上找；无 pyproject.toml → 返回 cur；签名 1 参数 start 无默认；__module__/__qualname__
- **ManifestError**：is Exception subclass；is BaseException subclass；mro 含 Exception；__module__/__qualname__；str 含 message；args == (message,)；repr 含 class name；raise/catch；catch as Exception；无 errors 属性
- **DocumentEntry frozen**：setattr → FrozenInstanceError；delattr → FrozenInstanceError；is_dataclass；10 fields；字段名顺序 doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations；frozen=True；__module__/__qualname__
- **ExpectedFailure frozen**：setattr/delattr → FrozenInstanceError；is dataclass；5 fields；字段名顺序 doc_id/path_str/resolved_path/expected_error_code/source_type；frozen=True；__module__/__qualname__
- **Manifest frozen**：setattr/delattr → FrozenInstanceError；is dataclass；5 fields manifest_version/devset_status/documents/expected_failures/project_root；frozen=True；__module__/__qualname__
- **Manifest property**：file_count == len(documents)；pdf_count == pdf 数；docx_count == docx 数；content_group_count 无 pairing 时 == file_count；一对配对（d1↔d2+d3）→ 2 组；自配对 d1↔d1 → 1 组；单向配对 d1→d2 → 1 组；空 documents → 0；categories_covered 去重+排序；空 → []；unicode（中文/english）→ 排序后；返回 list 不是 tuple；每次返回新 list
- **namespace 完整性**：json/dataclass/Path/Any/MANIFEST_VERSION/validate/ManifestError/DocumentEntry/ExpectedFailure/Manifest/load_manifest/_is_absolute_like/_has_backslash/_resolve_relative_path/_detect_project_root 都在；__all__ 是 list 不是 tuple；5 entries 精确；不含私有 helpers/constants
- **源码 token**：含 from __future__ import annotations、import json、from dataclasses import dataclass、from pathlib import Path、from typing import Any、from evaluation import MANIFEST_VERSION、from evaluation.schema import validate、class ManifestError、@dataclass(frozen=True)、class DocumentEntry/ExpectedFailure/Manifest、@property、manifest_version+MANIFEST_VERSION 检查、relative_to、frozenset；不含 print/import logging/import subprocess/import os/asyncio/abspath/realpath/.read_text(
- **docstring**：含 相对路径/绝对路径/反斜杠/项目根/本机

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 268 后）：24335 pass / 0 fail / 16 skip（HEAD `c321f86`）

### 下一步建议
- 候选 KE6：evaluation/annotation_metrics.py 第十七轮（194 行）
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE6（evaluation/annotation_metrics.py 第十七轮，194 行）继续推 evaluation。

---

## Round 269 — evaluation/annotation_metrics.py 第十七轮（98 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十七轮 edges 测试，覆盖 edges16 未触及的角度：chunk_boundary_prf 算法深度（stream.find 返回 -1 跳过 chunk；norm_chunks 含空字符串 chunk；所有 chunks 全空 → stream 空 → missing_markers；单 chunk → no_predicted_boundaries；position 缺字段默认 'after'；position 'middle' unknown 值 → after 路径；anchor 缺 marker 字段 → marker=''；tolerance_chars 0/negative/huge；multi pred 1 gt greedy closest；1 pred multi gt greedy closest；0 pred 0 gt；3 个相同 marker 顺序 search_from；输出 key 顺序；不修改 document/annotation；两次调用独立 dict）、figure_caption_prf 深度（document 是 dict 也 null；annotation 是 dict 也 null；both dict 仍 null；不修改 document/annotation；两次调用独立；每个 value 是 dict 含 value+reason）、PARSER_DOES_NOT_EMIT_RELATIONS（是 str/hashable/singleton）、namespace 完整性（Counter/Any/normalize_text/_null/_ratio/PARSER_DOES_NOT_EMIT_RELATIONS/figure_caption_prf/chunk_boundary_prf；__all__ 是 list 不是 tuple；3 entries；不含私有 helpers/constants）、签名 introspection（figure_caption_prf 2 参数无默认；chunk_boundary_prf 3 参数 tolerance_chars default 30；POSITIONAL_OR_KEYWORD；no var args/kw）、helper metadata（2 个 __module__/__qualname__；FunctionType）、源码 token 含 from __future__ import annotations/from collections import Counter/from typing import Any/from app.chunkers.structural import normalize_text/from evaluation.metrics import _null, _ratio/PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"/def figure_caption_prf/def chunk_boundary_prf/tolerance_chars: int = 30/used_pred = set()/used_gt = set()/used_pred.add(pi)/used_gt.add(gi)/continue/break/search_from/missing_markers/pairs.sort(key=lambda x: x[0])/2 * p_val * r_val// denom/denom <= 0；不含 print/import logging/import subprocess/import os/asyncio/import json/from pathlib、docstring 含 figure-caption/chunk_boundary/parser/heuristic/一对一/容差

### 改动
- 新增 `tests/test_annotation_metrics_edges17.py`（98 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **chunk_boundary_prf 算法深度**：stream.find 返回 -1 跳过 chunk；norm_chunks 含空字符串；所有 chunks 全空 → stream 空 → missing_markers；单 chunk → no_predicted_boundaries；position 缺字段 → 默认 'after'；position 'middle' → 走 else = after；anchor 缺 marker → marker='' → falsy → find_pos = -1 → missing；tolerance_chars 0 → 必须精确；negative → 永不匹配；huge → 任何距离匹配；2 pred 1 gt greedy → precision=0.5/recall=1.0；1 pred 2 gt greedy → precision=1.0/recall=0.5；0 pred 0 gt → no_predicted_boundaries；3 个相同 marker 顺序 search_from → 全匹配；输出 key 顺序 precision/recall/f1/_tolerance_chars；不修改 document/annotation；两次调用独立 dict
- **figure_caption_prf 深度**：返回 3 keys；所有 value None + reason=PARSER_DOES_NOT_EMIT_RELATIONS；document 是 dict（含 chunks/elements）也 null；annotation 是 dict（含 figure_caption_relations）也 null；both dict 仍 null；不修改 document/annotation；两次调用独立；每个 value 是 dict 含 value+reason
- **PARSER_DOES_NOT_EMIT_RELATIONS**：是 str；值精确 'parser_does_not_emit_relations'；hashable（可作 dict key）；module singleton
- **namespace 完整性**：Counter/Any/normalize_text/_null/_ratio/PARSER_DOES_NOT_EMIT_RELATIONS/figure_caption_prf/chunk_boundary_prf 都在；__all__ 是 list 不是 tuple；3 entries 精确；__all__ 不含 _null/_ratio/Counter/Any/normalize_text
- **签名 introspection**：figure_caption_prf 2 参数 document+annotation 无默认 POSITIONAL_OR_KEYWORD；no var args/kw；chunk_boundary_prf 3 参数 document+annotation+tolerance_chars default 30；POSITIONAL_OR_KEYWORD；no var args/kw
- **helper metadata**：figure_caption_prf/chunk_boundary_prf __module__ == 'evaluation.annotation_metrics'；__qualname__ 精确；FunctionType
- **源码 token**：含 from __future__ import annotations、from collections import Counter、from typing import Any、from app.chunkers.structural import normalize_text、from evaluation.metrics import _null, _ratio、PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"、def figure_caption_prf、def chunk_boundary_prf、tolerance_chars: int = 30、used_pred = set()、used_gt = set()、used_pred.add(pi)、used_gt.add(gi)、continue、break、search_from、missing_markers、pairs.sort(key=lambda x: x[0])、2 * p_val * r_val、/ denom、denom <= 0；不含 print/import logging/import subprocess/import os/asyncio/import json/from pathlib
- **docstring 内容**：是 str 长度>30；含 figure-caption；含 chunk_boundary 或 分块边界；含 parser+caption 或 relation；含 启发式 或 heuristic；含 一对一 或 one-to-one；含 容差 或 tolerance

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 269 后）：24433 pass / 0 fail / 16 skip（HEAD `6e98931`）

### 下一步建议
- 候选 KF6：evaluation/metrics.py 第十七轮（381 行）
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF6（evaluation/metrics.py 第十七轮，381 行）继续推 evaluation。

---

## Round 270 — evaluation/metrics.py 第十七轮（161 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十七轮 edges 测试，覆盖 edges16 未触及的角度：_null/_ratio/_bool_metric/_int_metric 详细（value 类型强制转换/reason 类型/keys 顺序/两次调用独立）、_is_valid_bbox 边界（valid int/float/mixed/太短/太长/空/含 bool/含 inf/含 nan/含 str/None/str/tuple/返回 bool）、_pdf_locator_ratio 边界（空/缺 source_locator/page=0/-1/float/str/text 缺 bbox/text 无效 bbox/text 有效 bbox/non-required 无需 bbox/部分 valid）、_docx_locator_ratio 边界（空/locator 有 page/bbox/structural_key/locator 空字典/locator None/缺/每个 structural_key 单独/部分 valid）、_image_resource_ratio 边界（无 image/全是非 image/image 缺 resource_path/empty resource_path/file not found/file 绝对路径/file 文件名 only/file size=0/部分 valid）、_chunk_reference_ratio 边界（空/elements 空/chunk 缺 source_element_ids/ids=[]/ids=None/id 不存在/部分匹配/all ids 都必须匹配）、_strip_unicode_whitespace 边界（空/无空白/ASCII 空格/\\t\\n\\r/NBSP/em space/ideographic space/line separator/paragraph separator/纯空白/不删非空白/不排序/返回 str）、_text_preservation 边界（both empty/all image/expected empty actual 非空/expected 非空 actual 空/perfect match/部分重叠/repeated chars 顺序不同/extra chars in actual/missing chars in actual/空白被忽略/3 keys 返回）、_heading_boundary_ratio 边界（无 heading/无 chunks/chunk 缺 source_element_ids/ids=[]/perfect match/部分 match/用第一个 id only）、_silent_drop_count 边界（无 expectations/empty expectations/无 element_count_by_type/empty element_count_by_type/actual > expected/actual == expected/actual < expected/多 type 求和/返回 int_metric）、compute_automatic_metrics 边界（document=None+error=None/document+error 都非 None/unknown source_type/pdf/docx 路径/14 keys when not failed/13 keys when failed/不修改 document/不修改 expectations/两次调用独立/schema_check_exception 路径）、namespace 完整性补强（_strip_unicode_whitespace/_bool_metric/_int_metric/math/Counter/Path/_TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED；__all__ == ['compute_automatic_metrics']）、常量精确（_TEXT_TYPES 7 items tuple；_PDF_BBOX_REQUIRED_TYPES 4 items tuple；_NOT_EVALUATED == 'not_evaluated'；subset；image 不在）、源码 token 补强（含 def _strip_unicode_whitespace/.isspace()/math.isfinite/删除全部 Unicode 空白/v1.1 或 v1.0/c_expected & c_actual；不含 print/import logging/import json/import subprocess/asyncio）、docstring（含 纯函数/不修改/text_preservation 或 文本保留）

### 改动
- 新增 `tests/test_evaluation_metrics_edges17.py`（161 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_null/_ratio/_bool_metric/_int_metric**：value 类型强制（_ratio 强制 float / _bool_metric 强制 bool / _int_metric 强制 int 截断）；reason 类型；keys 顺序 ['value','reason']；两次调用独立 dict；负数输入不验证（_ratio 接受任何 float）
- **_is_valid_bbox 边界**：valid int list / valid float list / mixed / 太短 / 太长 / 空 / 含 bool（True 是 int 子类但显式排除）/ 含 inf / 含 -inf / 含 nan / 含 str / None / str（不是 list）/ tuple（不是 list）/ 返回 bool
- **_pdf_locator_ratio 边界**：空 → null+no_elements；缺 source_locator → 0/1=0.0；page=0/-1 → 不计；page=1.0（float）→ 不计；page='1'（str）→ 不计；text 缺 bbox → 不计；text 无效 bbox → 不计；text 有效 bbox → 1.0；non-required（header/footer）无需 bbox；部分 valid → 0.5
- **_docx_locator_ratio 边界**：空 → null+no_elements；locator 有 page → 不计；有 bbox → 不计；有 structural_key → 1.0；locator 空字典 → 不计；locator None → 不计；缺 source_locator → 不计；每个 structural_key 单独触发；部分 valid → 0.5
- **_image_resource_ratio 边界**：无 image → null+no_image_elements；非 image only → null；image 缺 resource_path → 0.0；empty resource_path → 0.0；file not found → 0.0；file 绝对路径存在 → 1.0；file 文件名 only + image_base_dir 拼接 → 1.0；file size=0 → 0.0；部分 valid → 0.5
- **_chunk_reference_ratio 边界**：no_chunks → null+no_chunks；elements=[] → 0.0；chunk 缺 source_element_ids → 0.0；ids=[] → 0.0；ids=None → 0.0；id 不存在 → 0.0；部分 match → 0.5；all ids 都必须匹配（含一个不存在 → 0.0）
- **_strip_unicode_whitespace 边界**：空 → '';无空白 → 原样；ASCII 空格/\\t\\n\\r → 删；NBSP/em space/ideographic space/line separator/paragraph separator → 都删；纯空白 → '';不删非空白（标点 emoji）；不排序；返回 str
- **_text_preservation 边界**：both empty → equal=True + precision/recall null+empty_expected_and_actual；all image → expected='' actual='x' → equal=False precision=0.0 recall null+empty_expected；expected empty actual 非空 → equal=False precision=0.0 recall null；expected 非空 actual 空 → equal=False precision null recall=0.0；perfect match → 1.0/1.0；部分重叠 → 2/3；repeated chars 顺序不同 → equal=False 但 counter 相同 → precision/recall=1.0；extra chars → precision=2/3 recall=1.0；missing chars → precision=1.0 recall=2/3；空白被忽略；3 keys 返回
- **_heading_boundary_ratio 边界**：无 heading → null+no_heading_elements；无 chunks → 0.0；chunk 缺 source_element_ids → 0.0；ids=[] → 0.0；perfect match → 1.0；部分 match → 0.5；用 ids[0]（首元素）only
- **_silent_drop_count 边界**：无 expectations → null+no_expectations；empty expectations → null+no_expectations；无 element_count_by_type → null+no_expectations_element_count；empty element_count_by_type → null+no_expectations_element_count；actual > expected → 0；actual == expected → 0；actual < expected → 差值；多 type 求和；返回 int_metric
- **compute_automatic_metrics 边界**：document=None+error=None → pipeline_success=False+error_code value=None；document+error 都非 None → pipeline_success=False；unknown source_type → pdf/docx ratio 都 not_*_document；pdf 路径 → pdf_ratio null+no_elements + docx_ratio null+not_docx_document；docx 路径反之；14 keys when not failed；13 keys when failed（pipeline_failed）；不修改 document；不修改 expectations；两次调用独立；schema_check_exception 路径（monkeypatch document_passes_schema 抛错 → value=False + reason schema_check_exception:ValueError）
- **namespace 完整性补强**：_strip_unicode_whitespace/_bool_metric/_int_metric/math/Counter/Path/_TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED 都在；__all__ 是 list；__all__ == ['compute_automatic_metrics']
- **常量精确**：_TEXT_TYPES 7 items tuple（heading/paragraph/list_item/table/caption/header/footer）；_PDF_BBOX_REQUIRED_TYPES 4 items tuple（heading/paragraph/caption/list_item）；_NOT_EVALUATED == 'not_evaluated'；subset 关系；image 不在
- **源码 token 补强**：含 def _strip_unicode_whitespace/.isspace()/math.isfinite/删除全部 Unicode 空白/v1.1 或 v1.0/c_expected & c_actual；不含 print/import logging/import json/import subprocess/asyncio
- **docstring**：含 纯函数/不修改/text_preservation 或 文本保留

### 撞墙记录
- 0 fail（首次跑通过；修复了导入语句的语法错 `_compute_automatic_metrics if False else None` 笔误）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 270 后）：24594 pass / 0 fail / 16 skip（HEAD `5d8deb3`）

### 下一步建议
- 候选 KW6：evaluation/report.py 第十八轮（200 行）
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW6（evaluation/report.py 第十八轮，200 行）继续推 evaluation。

---

## Round 271 — evaluation/report.py 第十八轮（55 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：aggregate_summary 跨多 metric 组合（一个 doc 同时提供 ratio+count+success+silent_drop；不同 doc 提供 different metrics；macro_average 算术平均精确；macro_average 含 None 项；silent_drop_count 不污染 counts；ratio metric 不污染 counts；count metric 不污染 ratios；两次调用独立 dict；total 等于 len(per_doc)；pipeline_success 含 None 时 rate 计算）、build_provenance max_chars 接受 float/True/False/负 float（int() 截断）；build_provenance 时间戳格式；返回 dict 可 pickle；git_commit str-or-None-40-char；evaluator/report_version 来自 evaluation；max_chars 始终返回 int 类型；build_devset_section duck typing（任意含 6 属性对象）；缺属性 → AttributeError；get_dependency_versions keys 精确；pdfplumber 版本格式；无额外 keys；get_git_provenance 返回 dict 可 pickle；subprocess.run 用 cwd kwarg；returncode 非 0 处理；rev-parse 成功 status 空场景；status 非空 → dirty=True；_RATIO_METRICS 顺序深度（首= schema_valid；尾= chunk_boundary_f1；precision < recall < f1）；_COUNT_METRICS 单元素；_SUCCESS_BOOL_METRICS 单元素；源码 token 含 aggregate 循环/successes/total/sum(values)/len(values)/silent_drop_filter/timeout=10 ≥2/cwd=str(project_root)；不含 async/threading/numpy/pandas；模块 import 顺序（subprocess → datetime → pathlib → typing → evaluation）；docstring 提及 4 类聚合 + participating_docs + not_evaluated；异常路径（空 list 返回 4 keys；unknown metric 忽略；falsy-but-participating 值 0.0/False/0；silent_drop_count=0 参与；pipeline_success=False 计入 total）

### 改动
- 新增 `tests/test_evaluation_report_edges18.py`（55 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **aggregate_summary 跨多 metric 组合**：一个 doc 同时提供 4 类 metric → 4 buckets 都正确分组；不同 doc 提供 different metrics → participating_docs/not_evaluated 各自正确；macro_average = sum/len 算术平均；含 None 值不参与；silent_drop_count 不在 counts；ratio metric 不在 counts；count metric 不在 ratios；两次调用返回独立 dict（不缓存）；total = len(per_doc)（与 metric value 无关）；pipeline_success rate = success_count/total
- **build_provenance max_chars 类型转换**：max_chars=1.5 → int(1.5)=1；max_chars=-1.7 → int(-1.7)=-1（向 0 截断）；max_chars=True → 1；max_chars=False → 0；max_chars="800" → 800；始终返回 int 类型
- **build_provenance 输出**：可 pickle；run_timestamp_iso 是 str；git_commit 是 None 或 40-char str；evaluator_version == EVALUATOR_VERSION；report_version == REPORT_VERSION
- **build_devset_section duck typing**：任意含 6 属性（devset_status/file_count/content_group_count/pdf_count/docx_count/categories_covered）的对象都接受；缺属性 → AttributeError
- **get_dependency_versions**：keys 精确 == {'pdfplumber', 'python-docx', 'pypdfium2'}；pdfplumber 版本含 '.' 或 None；无额外 keys（len == 3）
- **get_git_provenance**：返回 dict 可 pickle；subprocess.run 用 cwd kwarg；rev-parse returncode=128 → commit=None；status returncode=128 → dirty=False；rev-parse 成功 + status 空 → dirty=False；status 非空 → dirty=True
- **_RATIO_METRICS 顺序**：首元素 == 'schema_valid'；尾元素 == 'chunk_boundary_f1'；chunk_boundary_precision 在 chunk_boundary_recall 前；chunk_boundary_recall 在 chunk_boundary_f1 前
- **_COUNT_METRICS / _SUCCESS_BOOL_METRICS**：均为单元素 list（element_count_total / pipeline_success）
- **源码 token 补强**：含 'for r in per_doc_results'/'sum('/'successes / total'/'if total else None'/'sum(values) / len(values)'/'r["metrics"].get("silent_drop_count", {})'/'timeout=10'（≥2 次）/'cwd=str(project_root)'；不含 'async '/'await '/'import threading'/'Thread('/'import numpy'/'import pandas'
- **import 顺序**：subprocess → datetime → pathlib → typing → evaluation（位置递增）
- **docstring**：提及 counts/success_rates/ratio/silent_drop 4 类；提及 participating（参与）；提及 not_evaluated（不参与/未评估）
- **异常路径**：空 list 返回 4 keys dict；unknown metric 被忽略（不在任一 bucket）；0.0 是 falsy 但参与 macro average；False 是 falsy 但参与 ratio；0 是 falsy 但参与 counts 求和；silent_drop_count=0 是 falsy 但参与求和；pipeline_success=False → success_count=0/total=1/rate=0.0

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 271 后）：24649 pass / 0 fail / 16 skip（HEAD `bf3c7a7`）

### 下一步建议
- 候选 KX6：evaluation/cli.py 第十九轮（243 行）
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KX6（evaluation/cli.py 第十九轮，243 行）继续推 evaluation。

---

## Round 272 — evaluation/cli.py 第十九轮（100 测试）

### 目标
- 给 `evaluation/cli.py`（243 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：_format_metric 精确字符串（'  ' 前缀；None value 用字面量 'null'；None reason fallback 'ok' 字面量；float .4f 精确格式：0.0000/1.0000/-0.5000；dict value ', ' 分隔；dict value sorted by key；str(value).lower() for bool；str value 走 fallback str(value)；list value 走 fallback；name:36 不截断；return str type）、_run_inspect_doc _sort_key 详细（输出含 'counts:' 标签；counts 行 'elements=N chunks=N'；'metrics:' header；file 行用 input_path；6 行顺序 file→document_id→source→parser→counts→metrics；counts 与 metrics 间空行；不同类型 metric 排序）、_run_inspect_doc lazy imports（figure_caption_prf/chunk_boundary_prf/compute_automatic_metrics 都在函数内 import；compute_automatic_metrics 调用含 image_base_dir=None；metrics.update ≥2 次）、main argv=None（走 sys.argv → SystemExit；空 list → SystemExit；返回类型是 int）、argparse _SubParsersAction 类型精确（first action 是 _HelpAction；choices.keys == {run, validate-report, inspect-doc}；choices 值是 ArgumentParser）、模块 source token（含 'choices=("fallback", "kreuzberg")'/'sys.stdout.reconfigure(encoding="utf-8", errors="replace")'/'hasattr(sys.stdout, "reconfigure")'/'清单不存在'/'清单加载失败'/'报告未通过 Schema 校验'/'evaluation-report.schema.json' ≥2 次/'.is_file()' ≥3 次/'[OK] 评测完成'/'通过 evaluation-report Schema 校验'/'return 2' ≥3/'return 1' ≥3/无 'return 3'/无负数 return；含 run_evaluation/load_manifest/validate_file/get_git_provenance 调用；含 ManifestError/EvalSchemaError import；不含 subprocess/logging/async/threading/os/shutil/tempfile）、模块 import 顺序（argparse→json→sys→pathlib→evaluation.manifest→evaluation.report→evaluation.runner→evaluation.schema 位置递增；4 个 evaluation 子模块 import 语句精确）、模块 docstring（提及 run/validate-report/inspect-doc/python -m evaluation.cli/sanity 或 开发期）、main 错误打印用 sys.stderr（run manifest missing/validate-report missing/inspect-doc missing）、_format_metric 与 _run_inspect_doc 联动（每行 metric 输出 '  ' 前缀；含 doc_id/source_path/parser_name 字段值显示）、_build_parser 详细（prog=='evaluation.cli' 精确；description 含 评测/校验/报告；formatter_class is RawDescriptionHelpFormatter；conflict_handler=='error'；add_help 默认 True；allow_abbrev is True；3 subparser 的 prog 含各自 name）、__main__ 块（含 SystemExit(main())；位于模块底部）

### 改动
- 新增 `tests/test_evaluation_cli_edges19.py`（100 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_format_metric 精确字符串**：所有输出 '  ' 前缀；None value 用 'null' 字面量；None value + reason=None 不 fallback 'ok'；bool/int/dict/float value + reason=None 用 'ok' fallback；float 0.0→'0.0000'/1.0→'1.0000'/0.123456→'0.1235'/-0.5→'-0.5000'；dict value 用 ', ' 分隔按 key sorted；bool True→'true'（小写）；str value→str(value) fallback；list value→str([1,2,3]) fallback；name:36 不截断；返回 str
- **_run_inspect_doc _sort_key 详细**：输出含 'counts:'/'metrics:' 标签；'elements=N chunks=N' 格式；file 行用 input_path；6 行顺序（file→document_id→source→parser→counts→metrics）位置递增；counts 与 metrics 间空行；不同 value 类型 metric 排序
- **_run_inspect_doc lazy imports**：figure_caption_prf/chunk_boundary_prf/compute_automatic_metrics 都在函数内 import；compute_automatic_metrics 调用含 image_base_dir=None；metrics.update 调用 ≥2 次（figure_caption + chunk_boundary）
- **main argv=None**：main(None) 走 sys.argv → SystemExit；main([]) → SystemExit；返回类型是 int（0/1/2）
- **argparse _SubParsersAction**：first action 是 _HelpAction；_SubParsersAction 单一；choices.keys == {run, validate-report, inspect-doc}；choices 值都是 ArgumentParser；run subparser 有 help 字符串
- **source token 补强**：含 'choices=("fallback", "kreuzberg")'/'sys.stdout.reconfigure(encoding="utf-8", errors="replace")'/'hasattr(sys.stdout, "reconfigure")'；含 '清单不存在'/'清单加载失败'/'报告未通过 Schema 校验'；含 'evaluation-report.schema.json' ≥2；含 '.is_file()' ≥3；含 '[OK] 评测完成'/'通过 evaluation-report Schema 校验'；含 'return 2' ≥3/'return 1' ≥3；不含 'return 3'/'return -1'/'return -2'；含 run_evaluation/load_manifest/validate_file/get_git_provenance 调用；含 ManifestError/EvalSchemaError；不含 subprocess/logging/async/threading/os/shutil/tempfile
- **import 顺序**：argparse→json→sys→pathlib→evaluation.manifest→evaluation.report→evaluation.runner→evaluation.schema 位置递增；4 个 evaluation 子模块 import 语句精确（'from evaluation.manifest import ManifestError, load_manifest'/'from evaluation.report import get_git_provenance'/'from evaluation.runner import run_evaluation'/'from evaluation.schema import EvalSchemaError, validate_file'）
- **docstring**：提及 run/validate-report/inspect-doc/python -m evaluation.cli/sanity 或 开发期
- **main 错误打印用 sys.stderr**：run manifest missing/validate-report missing/inspect-doc missing 都打印到 stderr；run manifest missing 时 stdout 为空
- **联动**：每行 metric 输出 '  ' 前缀；doc_id='abc-123'/source_path='/some/path.pdf'/parser_name='fallback' v1.0 都在输出中显示
- **_build_parser**：prog=='evaluation.cli'；description 含 评测/校验/报告；formatter_class is RawDescriptionHelpFormatter；conflict_handler=='error'；add_help 默认 True（_HelpAction 单一）；allow_abbrev is True；3 subparser 的 prog 含各自 name
- **__main__ 块**：含 SystemExit(main())；位于 main 函数定义之后

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 272 后）：24749 pass / 0 fail / 16 skip（HEAD `56ba52c`）

### 下一步建议
- 候选 KS6：evaluation/runner.py 第十九轮（227 行）
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KS6（evaluation/runner.py 第十九轮，227 行）继续推 evaluation。

---

## Round 273 — evaluation/runner.py 第十九轮（118 测试）

### 目标
- 给 `evaluation/runner.py`（227 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：_load_annotation source-level token（'path is None or not path.is_file()'/'encoding="utf-8"'/'except (OSError, json.JSONDecodeError)'/'return None' ≥2/'json.load(f)'/'path.open('/不含 print/logging）；_process_one source-level token（'"_per_doc"'/doc.doc_id/'out_stub.parent.mkdir(parents=True, exist_ok=True)'/'time.perf_counter()' ≥2/process_single(/write_json=False/doc.resolved_path/'image_output_dir_for(out_stub, document.source_hash)'/'out_stub.unlink()'/'except OSError:'/'"unknown"'/"process_single returned None without errors"/'errors[0].to_dict()'/'image_dir: Path | None = None'/return ≥3/不含 print/logging/subprocess）；run_evaluation source-level token（'output_root.mkdir(parents=True, exist_ok=True)'/'parser_version_for_prov'/'if parser_version and not parser_version_for_prov:'/'per_doc_results: list[dict[str, Any]] = []'/'for doc in manifest.documents:'/compute_automatic_metrics(/'image_base_dir='/'_load_annotation(doc.annotation_resolved)'/'figure_caption_prf(document, annotation)'/'chunk_boundary_prf(/'tolerance_chars=tolerance_chars'/'metrics.update(' ≥2/'chunk_b.pop("_tolerance_chars", None)'/'chunk_b.pop("_missing_markers", None)'/'"_annotation_present": annotation is not None'/'"_tolerance_chars":'/'"_missing_markers":'/'for ef in manifest.expected_failures:'/ef.resolved_path/'actual_code = errors[0].code if errors else None'/'"matches": actual_code == ef.expected_error_code'/build_provenance(/build_devset_section(manifest)/aggregate_summary(per_doc_results)/'public_per_doc = []'/report 6 keys 字段精确/'json.dump(report, f, ensure_ascii=False, indent=2)'/'"wall_time_seconds":'/'"total": total_seconds'/'"parse": None'/'"chunk": None'/'"parse_reason": "not_instrumented"'/'"chunk_reason": "not_instrumented"'/'return report'/不含 print/logging/subprocess/concurrent.futures）；模块 imports 精确字符串（4 个 evaluation 子模块 import）；import 顺序（__future__→json→time→pathlib→typing→app.pipeline→evaluation→evaluation.annotation_metrics→evaluation.metrics→evaluation.report）；__all__ 精确；namespace has；签名精确（5 params；3 keyword-only；2 positional-or-keyword）；docstring 含 total/perf_counter/not_instrumented/pipeline_failed/image_resource 或 image_output_dir/pipeline；run_evaluation 行为（top-level 6 keys 顺序；empty manifest → per_doc=[]；devset keys；summary 4 buckets；provenance 含 4 必需 keys；expected_failures list；report_version is str；写盘 JSON 可解析；ensure_ascii=False → 无 \u 转义；indent=2 → 含 \n 与 "  "；两次调用独立 dict）

### 改动
- 新增 `tests/test_evaluation_runner_edges19.py`（118 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **_load_annotation source token**：含 'path is None or not path.is_file()'/'encoding="utf-8"'/'except (OSError, json.JSONDecodeError)'/'return None' ≥2/'json.load(f)'/'path.open('；不含 print/logging
- **_process_one source token**：含 '"_per_doc"'/doc.doc_id/'out_stub.parent.mkdir(parents=True, exist_ok=True)'/'time.perf_counter()' ≥2/process_single(/write_json=False/doc.resolved_path/'image_output_dir_for(out_stub, document.source_hash)'/'out_stub.unlink()'/'except OSError:'/'"unknown"'/"process_single returned None without errors"/'errors[0].to_dict()'/'image_dir: Path | None = None'/return ≥3；不含 print/logging/subprocess
- **run_evaluation source token**：含 output_root mkdir/parser_version_for_prov 收集/per_doc_results list init/documents loop/compute_automatic_metrics 调用/image_base_dir kwarg/_load_annotation 调用/figure_caption_prf 调用/chunk_boundary_prf 调用/metrics.update ≥2/tolerance_record pop/missing_markers pop/_annotation_present field/_tolerance_chars field/_missing_markers field/expected_failures loop/ef.resolved_path/actual_code pattern/matches pattern/build_provenance 调用/build_devset_section 调用/aggregate_summary 调用/public_per_doc loop/report 6 keys 字段精确/json.dump 调用/wall_time_seconds 5 keys（total/parse/chunk/parse_reason/chunk_reason）/return report；不含 print/logging/subprocess/concurrent.futures
- **模块 imports 精确**：'from app.pipeline import image_output_dir_for, process_single'；'from evaluation import REPORT_VERSION'；'from evaluation.annotation_metrics import' 含 chunk_boundary_prf/figure_caption_prf；'from evaluation.metrics import compute_automatic_metrics'；'from evaluation.report import' 含 aggregate_summary/build_devset_section/build_provenance
- **import 顺序**：__future__→json→time→pathlib→typing→app.pipeline→evaluation→evaluation.annotation_metrics→evaluation.metrics→evaluation.report 位置递增
- **__all__ 精确**：m.__all__ == ['run_evaluation']；is list type
- **namespace**：含 _load_annotation/_process_one/run_evaluation/REPORT_VERSION/time/json/Path/Any；不含 subprocess/logging/os/asyncio/threading
- **签名精确**：_load_annotation 1 param 名 path；_process_one 4 params（doc/output_root/parser_name/max_chars）；run_evaluation 5 params（manifest/output_path/parser_name/max_chars/tolerance_chars）；3 keyword-only；2 positional-or-keyword
- **docstring**：含 total/perf_counter/not_instrumented/pipeline_failed/image_resource 或 image_output_dir/pipeline
- **run_evaluation 行为**：top-level 6 keys 顺序 ['report_version','provenance','devset','summary','per_doc','expected_failures']；empty manifest → per_doc=[]；devset 含 status/file_count；summary 4 buckets（counts/success_rates/ratio_macro_averages/silent_drop_total）；provenance 含 evaluator_version/report_version/parser_name/max_chars；expected_failures 是 list；report_version 是 str == REPORT_VERSION；写盘 JSON 可重新解析；ensure_ascii=False → 无 \u 转义；indent=2 → 含 \n 与 "  "；两次调用独立 dict（per_doc/provenance 不共享）

### 撞墙记录
- 12 fail 首次跑（已修复）：
  - test_run_evaluation_signature_param_count_4：实际 5 params（manifest/output_path/parser_name/max_chars/tolerance_chars）；改为 count==5
  - 11 个 Manifest 构造错误：file_count 等是 property 不是 ctor 参数；用 _make_empty_manifest helper 正确构造 Manifest(manifest_version/devset_status/documents/expected_failures/project_root)

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 273 后）：24867 pass / 0 fail / 16 skip（HEAD `6328ad5`）

### 下一步建议
- 候选 KZ6：evaluation/schema.py 第十二轮（80 行）
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KZ6（evaluation/schema.py 第十二轮，80 行，最小模块）继续推 evaluation。

---

## Round 274 — evaluation/schema.py 第十二轮（110 测试）

### 目标
- 给 `evaluation/schema.py`（80 行）加第十二轮 edges 测试，覆盖 edges11 未触及的角度：SCHEMAS_DIR 定义精确字符串（'Path(__file__).resolve().parent.parent / "schemas"'；parent 含 pyproject.toml；parent.parent 是 evaluation 目录；value 是 resolved Path）；_schema_path source-level token（'SCHEMAS_DIR / name'/'p.is_file()'/'raise FileNotFoundError(f"Schema 文件不存在: {p}")'/'return p'）；_schema_path 未知 name 错误信息含 'Schema 文件不存在' 字面量 + 完整路径；load_schema source-level token（'_schema_path(name).open("r", encoding="utf-8")'/'json.load(f)'/'return json.load(f)'；不含 print/logging）；validate source-level token（'schema = load_schema(schema_name)'/'Draft202012Validator(schema)'/'sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))'/'if not errors:'/'flat: list[dict[str, Any]] = []'/'for err in errors:'/'flat.append('/3 keys 字面量精确顺序 path/message/schema_path/'head = errors[0]'/'raise EvalSchemaError('/message format 含 '校验失败'/'len(errors)'/'head.message'/'list(head.absolute_path)'；不含 print/logging/subprocess/async）；validate_file source-level token（'p = Path(path)'/'if not p.is_file():'/'raise FileNotFoundError'/'待校验文件不存在'/'open("r", encoding="utf-8")'/'json.load(f)'/'validate(data, schema_name)'；不含 print/logging）；EvalSchemaError source-level token（'class EvalSchemaError(Exception):'/'super().__init__(message)'/'self.errors = errors or []'；不含 print/logging）；__all__ source 5 entries 精确顺序（SCHEMAS_DIR → EvalSchemaError → load_schema → validate → validate_file）；模块 import 顺序（__future__→json→pathlib→typing→jsonschema→JSValidationError→SCHEMAS_DIR）；JSValidationError 在 namespace 中（实际未使用）；不含 lru_cache/threading/os.system/silent_drop_count/metrics/process_single/runner/report 引用；无 __main__ 块；3 个 schema 顶层含 '$schema'/'properties'；validate 失败时 errors 项含 path/message/schema_path 3 keys；path 是 list/message 是 str/schema_path 是 list；两次调用产生独立 errors lists；message 含 'Schema \'{name}\' 校验失败 (' + '处)：' + '@ path=' 字面量；EvalSchemaError.args / errors 默认空 list / 显式 errors 保留引用；validate_file 接受 str 路径 + 返回 None；模块所有 helper 是 FunctionType；EvalSchemaError 是 class；SCHEMAS_DIR 是 Path 实例；docstring 含 manifest/annotation/evaluation-report/app/schema.py/业务或评测；_schema_path 返回 Path 含 .json 后缀 / 'manifest' stem / parent 是 SCHEMAS_DIR；load_schema 返回非空 dict；不缓存（每次新读盘）；minimal valid manifest 通过；load_schema → _schema_path 调用链；validate_file → validate 调用链；validate → load_schema 调用链

### 改动
- 新增 `tests/test_evaluation_schema_edges12.py`（110 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **SCHEMAS_DIR 定义**：'Path(__file__).resolve().parent.parent / "schemas"' 精确；parent 含 pyproject.toml；parent.parent 是 evaluation 目录；value 是 resolved Path（== .resolve()）
- **_schema_path source token**：含 'SCHEMAS_DIR / name'/'if not p.is_file():'/'raise FileNotFoundError(f'/'Schema 文件不存在'/'return p'；未知 name 错误信息含完整路径 + 'Schema 文件不存在' + 'nonexistent.schema.json' + 'schemas'
- **load_schema source token**：含 '_schema_path(name)'/'open("r", encoding="utf-8")'/'json.load(f)'/'return json.load(f)'；不含 print/logging
- **validate source token**：含 'schema = load_schema(schema_name)'/'Draft202012Validator(schema)'/'validator.iter_errors(instance)'/'sorted + key=lambda'/'if not errors:'/'flat: list[dict[str, Any]] = []'/'for err in errors:'/'flat.append('/3 keys 字面量精确/'head = errors[0]'/'raise EvalSchemaError('/校验失败/len(errors)/head.message/list(head.absolute_path)；不含 print/logging/subprocess/async
- **validate_file source token**：含 'p = Path(path)'/'if not p.is_file():'/'raise FileNotFoundError'/'待校验文件不存在'/'open("r", encoding="utf-8")'/'json.load(f)'/'validate(data, schema_name)'；不含 print/logging
- **EvalSchemaError source token**：含 'class EvalSchemaError(Exception):'/'super().__init__(message)'/'self.errors = errors or []'；不含 print/logging；直接继承 Exception
- **__all__ 5 entries 顺序精确**：SCHEMAS_DIR → EvalSchemaError → load_schema → validate → validate_file
- **import 顺序**：__future__→json→pathlib→typing→jsonschema→JSValidationError→SCHEMAS_DIR 定义
- **JSValidationError**：在 namespace 中；import 语句精确
- **不含禁止内容**：lru_cache/threading/os.system/silent_drop_count/metrics/process_single/runner/report/__main__ 块
- **3 schema 实际加载**：每个含 '$schema'/'properties' 顶层字段
- **validate 行为**：失败时 errors 项含 path/message/schema_path 3 keys；path 是 list/message 是 str/schema_path 是 list；两次调用产生独立 errors lists；message 含 'Schema \'{name}\' 校验失败 (' + '处)：' + '@ path=' 字面量
- **EvalSchemaError 行为**：args == (message,)；errors 默认空 list；显式 errors 保留引用；str 不强制含 errors
- **validate_file 行为**：str 路径接受；返回 None；错误信息含 '待校验文件不存在'
- **模块 metadata**：__file__ 路径以 evaluation/schema.py 结尾；3 helpers 是 FunctionType；EvalSchemaError 是 class；SCHEMAS_DIR 是 Path 实例
- **docstring**：含 manifest/annotation/evaluation-report/app/schema.py/业务 或 评测；第一行含 Schema
- **调用链**：load_schema → _schema_path；validate_file → validate；validate → load_schema（用 monkeypatch 验证）

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 274 后）：24977 pass / 0 fail / 16 skip（HEAD `54c71ee`）

### 下一步建议
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KE7：evaluation/annotation_metrics.py 第十八轮（194 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KE7（evaluation/annotation_metrics.py 第十八轮，194 行）继续推 evaluation。

---

## Round 275 — evaluation/annotation_metrics.py 第十八轮（149 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（194 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：模块 imports 精确字符串（'from collections import Counter'/'from typing import Any'/'from app.chunkers.structural import normalize_text'/'from evaluation.metrics import _null, _ratio'）；import 顺序（__future__→collections→typing→app.chunkers.structural→evaluation.metrics→PARSER_DOES_NOT_EMIT_RELATIONS）；PARSER_DOES_NOT_EMIT_RELATIONS source-level 定义精确；figure_caption_prf source-level token（'reason = PARSER_DOES_NOT_EMIT_RELATIONS'/'return {' 3 keys 字面量；不含 normalize_text 调用/print/subprocess）；三次 _null 调用产生独立 dict（_null 不缓存）；每个 dict 含 value/reason 2 keys；value is None；reason == PARSER_DOES_NOT_EMIT_RELATIONS；不修改 document/annotation；两次调用独立；chunk_boundary_prf source-level token 详尽（'out: dict[str, dict[str, Any]] = {}'/'if document is None:'/'_null("pipeline_failed")'/_null("no_annotation")/'if not chunks or len(chunks) < 2:'/'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]'/'joined_raw = " ".join(norm_chunks)'/'stream = normalize_text(joined_raw)'/'predicted: list[int] = []'/'find_pos = stream.find(txt, pos)'/'gt_positions: list[int] = []'/'missing_markers: list[str] = []'/'search_from = 0'/'marker = a.get("marker", "")'/'position = a.get("position", "after")'/'find_pos = stream.find(marker, search_from) if marker else -1'/'pairs: list[tuple[int, int, int]] = []'/'used_pred = set()'/'used_gt = set()'/'d = abs(pv - gv)'/'if d <= tolerance_chars:'/'pairs.append((d, pi, gi))'/'pairs.sort(key=lambda x: x[0])'/'matched = 0'/'used_pred.add(pi)'/'used_gt.add(gi)'/'matched += 1'/'num_pred = len(predicted)'/'num_gt = len(gt_positions)'/'p_val = out["chunk_boundary_precision"]["value"]'/'if p_val is None or r_val is None:'/'denom = p_val + r_val'/'if denom <= 0:'/'2 * p_val * r_val / denom'/'out["_tolerance_chars"] = ...'/'out["_missing_markers"] = ...'/'if missing_markers:'）；6 个 reason 常量精确（'pipeline_failed'/'no_annotation'/'no_predicted_boundaries'/'no_ground_truth_anchors'/'no_ground_truth_anchors_in_stream'/'precision_or_recall_not_evaluated'）；不含 print/logging/subprocess/async/threading/os/json import/silent_drop_count/element_count_total/image_resource/pdf_locator/docx_locator/process_single；算法步骤编号 1./2./3./4./5. 注释存在；__all__ 3 entries 顺序精确；namespace has；helper metadata；签名 introspection 详尽；模块 docstring 含 figure-caption/chunk_boundary/P/R/F1/一对一/容差/parser

### 改动
- 新增 `tests/test_annotation_metrics_edges18.py`（149 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块 imports 精确**：4 个 import 语句精确字符串；import 顺序正确
- **PARSER_DOES_NOT_EMIT_RELATIONS**：source-level 定义精确；value 精确 'parser_does_not_emit_relations'；类型是 str
- **figure_caption_prf source token**：含 'reason = PARSER_DOES_NOT_EMIT_RELATIONS'；含 3 keys 字面量；不含 normalize_text/print/subprocess
- **figure_caption_prf 行为**：三次 _null 调用产生独立 dict；每个 dict 含 value/reason 2 keys；value is None；reason == PARSER_DOES_NOT_EMIT_RELATIONS；不修改 document/annotation；两次调用独立
- **chunk_boundary_prf source token 详尽**：所有关键代码 token 验证（含 50+ source-level 断言）
- **6 个 reason 常量精确**：'pipeline_failed'/'no_annotation'/'no_predicted_boundaries'/'no_ground_truth_anchors'/'no_ground_truth_anchors_in_stream'/'precision_or_recall_not_evaluated' 都在源码中
- **不含禁止内容**：print/logging/subprocess/async/threading/os/json import/silent_drop_count/element_count_total/image_resource/pdf_locator/docx_locator/process_single
- **算法步骤编号**：1./2./3./4./5. 注释都在
- **__all__**：3 entries 顺序 ['PARSER_DOES_NOT_EMIT_RELATIONS', 'figure_caption_prf', 'chunk_boundary_prf']；不含 _null/_ratio/normalize_text/Counter/Any
- **namespace**：含 Counter/Any/normalize_text/_null/_ratio/PARSER_DOES_NOT_EMIT_RELATIONS/figure_caption_prf/chunk_boundary_prf；不含 subprocess/logging/os/asyncio/json/threading/Path
- **chunk_boundary_prf 行为**：document None → 'pipeline_failed' 三 metric + _tolerance_chars；annotation falsy → 'no_annotation' 三 metric；chunks <2 + 无 anchors → 'no_predicted_boundaries' 三 metric；chunks <2 + 有 anchors → precision/f1 是 'no_predicted_boundaries'，recall 是 _ratio(0.0)；有 chunks 无 anchors → 'no_ground_truth_anchors'；不修改 document/annotation；两次调用独立；_tolerance_chars.value 是 int；_missing_markers.value 是 list；完美匹配 → 1.0/1.0/1.0；无匹配 → 0.0/0.0/0.0；value 类型是 float
- **helper metadata**：figure_caption_prf/chunk_boundary_prf 都是 FunctionType；__module__ == 'evaluation.annotation_metrics'；__qualname__ 精确
- **签名 introspection**：figure_caption_prf 2 params（document/annotation）无默认值 positional-or-keyword；chunk_boundary_prf 3 params（document/annotation/tolerance_chars），tolerance_chars 默认 30 positional-or-keyword
- **docstring**：含 figure-caption/chunk_boundary/P/R/F1/一对一/容差/parser

### 撞墙记录
- 2 fail 首次跑（已修复）：
  - test_chunk_boundary_prf_chunks_lt_2_returns_no_predicted_boundaries：chunks <2 + 有 anchors → recall 是 _ratio(0.0)（reason None），不是 'no_predicted_boundaries'；拆成两个测试分别测「无 anchors」和「有 anchors」路径
  - test_chunk_boundary_prf_chunks_lt_2_with_no_anchors_recall_is_zero_ratio：原意错——「无 anchors」路径 recall 是 _null('no_predicted_boundaries')，「有 anchors」才是 _ratio(0.0)；改名为 _with_anchors_recall_is_zero_ratio 并断言正确分支

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 275 后）：25126 pass / 0 fail / 16 skip（HEAD `eb1c504`）

### 下一步建议
- 候选 KT7：evaluation/manifest.py 第十九轮（239 行）
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KT7（evaluation/manifest.py 第十九轮，239 行）继续推 evaluation。

---

## Round 276 — evaluation/manifest.py 第十九轮（169 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：模块 imports 精确字符串（'import json'/'from dataclasses import dataclass'/'from pathlib import Path'/'from typing import Any'/'from evaluation import MANIFEST_VERSION'/'from evaluation.schema import validate'）；import 顺序；ManifestError source-level（class 定义 + docstring '清单加载或校验失败' + 不含 __init__ + 不含 print + bases==(Exception,)）；_is_absolute_like source-level token（'if not path_str:'/'path_str.startswith("/")'/'len(path_str) >= 3'/'path_str[1] == ":"'/'path_str[0].isalpha()'/'path_str[2] in ("\\\\", "/")'/'return True' ≥2/'return False'；返回 bool；__qualname__ 精确）；_has_backslash source-level（'return "\\\\" in path_str' 单行；返回 bool）；DocumentEntry/ExpectedFailure/Manifest source-level（@dataclass(frozen=True) 装饰器 + class 定义 + fields 顺序精确 + field count 精确 + frozen setattr/delattr raises）；Manifest properties source-level（file_count 'return len(self.documents)'；pdf_count 'd.source_type == "pdf"'；docx_count 'd.source_type == "docx"'；content_group_count 含 set[frozenset]/unpaired/groups/seen.update/return groups + unpaired；categories_covered 含 s.update + return sorted(s)）；_resolve_relative_path source-level（'if not path_str:'/'为空'/'if _is_absolute_like'/'禁止绝对路径'/'if _has_backslash'/'禁止反斜杠'/'(project_root / path_str).resolve()'/'resolved.relative_to(project_root_resolved)'/'except ValueError:'/'项目根目录之外'/'return resolved'；不含 print）；load_manifest source-level（'p = Path(manifest_path).resolve()'/'if not p.is_file():'/'清单文件不存在'/'if project_root is None:'/'_detect_project_root(p)'/'Path(project_root).resolve()'/'open("r", encoding="utf-8")'/'data = json.load(f)'/'except json.JSONDecodeError as e:'/'清单 JSON 解析失败'/'validate(data, "manifest.schema.json")'/'data.get("manifest_version") != MANIFEST_VERSION'/'manifest_version 不兼容'/'documents: list[DocumentEntry] = []'/'failures: list[ExpectedFailure] = []'/'return Manifest('；不含 print/logging/subprocess/async）；_detect_project_root source-level（'cur = start.resolve()'/'if cur.is_file():'/'cur = cur.parent'/'for parent in [cur, *cur.parents]:'/'pyproject.toml'/'return parent'/'return cur'；不含 print）；__all__ 5 entries 顺序精确；namespace has（MANIFEST_VERSION/validate/ManifestError/Manifest/DocumentEntry/ExpectedFailure/load_manifest + 4 helpers；不含 subprocess/logging/os/asyncio/threading）；模块 source 不含 print/logging/subprocess/async/threading/os/read_text/write_text/silent_drop_count/compute_automatic_metrics/image_resource/process_single；load_manifest 实际加载 minimal manifest 返回 Manifest 实例；不存在的文件 → ManifestError 含 '清单文件不存在'；invalid JSON → ManifestError 含 '清单 JSON 解析失败'；manifest_version 不匹配 → ManifestError 或 EvalSchemaError；两次调用返回独立 Manifest；签名 introspection（5 个 helper 都精确）；docstring 含相对路径/正斜杠/绝对路径/反斜杠/项目根；helper metadata（5 个 FunctionType + 4 个 dataclass）

### 改动
- 新增 `tests/test_evaluation_manifest_edges19.py`（169 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块 imports 精确**：6 个 import 语句精确字符串；import 顺序 __future__→json→dataclasses→pathlib→typing→evaluation→evaluation.schema
- **ManifestError source-level**：'class ManifestError(Exception):' + docstring '清单加载或校验失败' + 不含 __init__ + 不含 print + bases==(Exception,)；is Exception+BaseException subclass；__module__/__qualname__ 精确；raise+catch 行为
- **_is_absolute_like source-level**：所有 7 个关键 token 精确；return True ≥2；return False；返回 bool；__qualname__ 精确
- **_has_backslash source-level**：'return "\\\\" in path_str' 单行函数；返回 bool
- **DocumentEntry/ExpectedFailure/Manifest source-level**：@dataclass(frozen=True) 装饰器 + class 定义；fields 顺序精确；field count 精确（DocumentEntry 10 / ExpectedFailure 5 / Manifest 5）；frozen setattr/delattr raises FrozenInstanceError
- **Manifest properties source-level**：5 properties 体内关键 token 都验证；返回类型 int/int/int/int/list
- **_resolve_relative_path source-level**：所有 11 个关键 token 精确；不含 print；成功路径返回 Path；空 path → ManifestError 含 '为空'；absolute → '禁止绝对路径'；backslash → '禁止反斜杠'
- **load_manifest source-level**：所有 20+ 个关键 token 精确；不含 print/logging/subprocess/async
- **_detect_project_root source-level**：所有 7 个关键 token 精确；不含 print；实际找到/找不到 pyproject.toml 都返回 Path
- **__all__ 5 entries 顺序**：ManifestError → Manifest → DocumentEntry → ExpectedFailure → load_manifest；不含 4 个 helper / MANIFEST_VERSION
- **namespace**：含 MANIFEST_VERSION（== evaluation.MANIFEST_VERSION）；validate（is evaluation.schema.validate）；5 dataclass+function；4 helper；不含 subprocess/logging/os/asyncio/threading
- **不含禁止内容**：print/logging/subprocess/async/threading/os/read_text/write_text/silent_drop_count/compute_automatic_metrics/image_resource/process_single 都不在 source 中
- **load_manifest 行为**：minimal manifest 返回 Manifest 实例（manifest_version/devset_status/documents/expected_failures/project_root 正确）；不存在的文件 → ManifestError 含 '清单文件不存在'；invalid JSON → ManifestError 含 '清单 JSON 解析失败'；不匹配 version → ManifestError 或 EvalSchemaError；两次调用返回独立 Manifest 但 == 相等
- **签名 introspection**：_is_absolute_like 1 param name path_str；_has_backslash 1 param；_resolve_relative_path 3 params（path_str/project_root/field_name）；load_manifest 2 params（manifest_path/project_root 默认 None）；_detect_project_root 1 param name start
- **docstring**：含相对路径/正斜杠/绝对路径/反斜杠/项目根
- **helper metadata**：5 个 helper 都是 FunctionType；Manifest/DocumentEntry/ExpectedFailure 都是 type；ManifestError 是 type

### 撞墙记录
- 0 fail（首次跑通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 276 后）：25295 pass / 0 fail / 16 skip（HEAD `325b453`）

### 下一步建议
- 候选 KF7：evaluation/metrics.py 第十八轮（381 行）
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KF7（evaluation/metrics.py 第十八轮，381 行）继续推 evaluation。

---

## Round 277 — evaluation/metrics.py 第十八轮（169 测试）

### 目标
- 给 `evaluation/metrics.py`（381 行）加第十八轮 edges 测试，覆盖 edges17 未触及的角度：模块 imports 精确字符串（'import math'/'from collections import Counter'/'from pathlib import Path'/'from typing import Any'）；import 顺序；_null source（'return {"value": None, "reason": reason}'）；_ratio source（'return {"value": float(value), "reason": None}'；不含 int(value)）；_bool_metric source（'return {"value": bool(value), "reason": None}'）；_int_metric source（'return {"value": int(value), "reason": None}'）；常量精确（_TEXT_TYPES 7 items tuple；_PDF_BBOX_REQUIRED_TYPES 4 items tuple；_NOT_EVALUATED == 'not_evaluated'；subset 关系；image 不在；table/header/footer 不在 PDF_BBOX）；常量 source 定义精确；compute_automatic_metrics source 详尽（metrics init/pipeline_success 表达式/_bool_metric 调用/error_code 赋值/document is None 检查/11 metric names loop/schema_valid 分支/延迟 schema_validation import/try+except+exception type 名/elements+chunks 获取/_int_metric 调用/by_type loop + 7 keys/source_type 分支/各 sub-function 调用/return metrics）；_pdf_locator_ratio source（empty check/locator get/page int 检查/continue/_PDF_BBOX_REQUIRED_TYPES 引用/bbox get/_is_valid_bbox 调用/return _ratio）；_docx_locator_ratio source（7 structural_keys 精确/page or bbox 检查/any structural_key 检查）；_is_valid_bbox source（list + len 4 检查/bool 检查/int+float 检查/isfinite 检查/return True）；_image_resource_ratio source（images comprehension/no_images check/rp get/not rp check/candidates list/image_base_dir 检查/is_file + size 检查/OSError catch）；_chunk_reference_ratio source（no_chunks check/elem_ids set comprehension/ids get/all 检查）；_strip_unicode_whitespace source（'return "".join(ch for ch in s if not ch.isspace())'；不含 s.strip()/.replace()）；_text_preservation source（expected_raw join/content get/image filter/actual_raw join/strip 调用/equal 检查/empty both check/Counter 交集/empty_actual check/empty_expected check/3 keys return）；_heading_boundary_ratio source（headings comprehension/no_headings check/chunk_first_ids set/ids[0]/matched sum/return ratio）；_silent_drop_count source（no_expectations check/expected_counts get/no_expected_counts check/drops init/items loop/actual<exp check/return int_metric）；__all__ 精确（['compute_automatic_metrics']）；namespace 完整（4 helpers + compute + 9 sub-helpers + 3 constants + math/Counter/Path/Any；不含 subprocess/logging/json/os/asyncio/threading）；模块 source 不含 print/logging/subprocess/async/threading/json/os/process_single(调用)/figure_caption/chunk_boundary；compute_automatic_metrics 不修改 document/expectations；两次调用独立 dict；keys count when failed=14/when succeeded=14；keys exact set；helper metadata（14 个 FunctionType；__module__ == 'evaluation.metrics'）；签名 introspection（5 params；image_base_dir 默认 None；document/error 无默认；no var args/kwargs）；docstring 含 纯函数/不修改/text_preservation/不丢不重/Counter/v1.1/空白

### 改动
- 新增 `tests/test_evaluation_metrics_edges18.py`（169 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块 imports 精确**：4 import 语句精确；import 顺序 __future__→math→collections→pathlib→typing
- **_null source**：'return {"value": None, "reason": reason}'；signature 1 param name reason
- **_ratio source**：'return {"value": float(value), "reason": None}'；不含 int(value)；signature 1 param
- **_bool_metric source**：'return {"value": bool(value), "reason": None}'
- **_int_metric source**：'return {"value": int(value), "reason": None}'
- **常量精确**：_TEXT_TYPES 7 items tuple；_PDF_BBOX_REQUIRED_TYPES 4 items tuple；_NOT_EVALUATED == 'not_evaluated'；subset 关系；image/table/header/footer 不在 PDF_BBOX；source 定义精确
- **compute_automatic_metrics source**：所有关键 token 验证（30+ source-level 断言）
- **_pdf_locator_ratio source**：所有 9 个关键 token 精确
- **_docx_locator_ratio source**：7 structural_keys 精确；page or bbox 检查；any structural_key 检查
- **_is_valid_bbox source**：所有 6 个关键 token 精确
- **_image_resource_ratio source**：所有 9 个关键 token 精确
- **_chunk_reference_ratio source**：所有 4 个关键 token 精确
- **_strip_unicode_whitespace source**：'return "".join(ch for ch in s if not ch.isspace())'；不含 s.strip()/.replace()
- **_text_preservation source**：所有 12+ 关键 token 精确
- **_heading_boundary_ratio source**：所有 6 个关键 token 精确
- **_silent_drop_count source**：所有 7 个关键 token 精确
- **__all__**：['compute_automatic_metrics'] 单元素 list
- **namespace**：4 helpers + compute + 9 sub-helpers + 3 constants + math/Counter/Path/Any 都在；不含 subprocess/logging/json/os/asyncio/threading
- **不含禁止内容**：print/logging/subprocess/async/threading/json/os/process_single 调用/figure_caption/chunk_boundary 都不在 source 中
- **compute_automatic_metrics 行为**：不修改 document/expectations；两次调用独立 dict；返回 dict type；keys count=14（failed+succeeded 都 14）；keys exact set 验证
- **helper metadata**：14 个 helper 都是 FunctionType；__module__ == 'evaluation.metrics'
- **签名 introspection**：compute_automatic_metrics 5 params（document/error/source_type/expectations/image_base_dir）；image_base_dir 默认 None；document/error 无默认；no var args/kwargs
- **docstring**：含 纯函数/不修改/text_preservation/不丢不重/Counter/v1.1/空白

### 撞墙记录
- 1 fail 首次跑（已修复）：
  - test_module_source_does_not_contain_process_single：docstring 含 'process_single 返回的 Document.to_dict()' 字符串，断言失败；改为 test_module_source_does_not_contain_process_single_call，检查 'process_single(' 调用而非字符串

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 277 后）：25464 pass / 0 fail / 16 skip（HEAD `15f2328`）

### 下一步建议
- 候选 KW7：evaluation/report.py 第十九轮（200 行）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 KW7（evaluation/report.py 第十九轮，200 行）继续推 evaluation。

---

## Round 278 — evaluation/report.py 第十九轮（149 测试）

### 目标
- 给 `evaluation/report.py`（200 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：模块 imports 精确字符串（5 import 语句精确：'from __future__ import annotations'、'import subprocess'、'from datetime import datetime'、'from pathlib import Path'、'from typing import Any'）；import 顺序；_RATIO_METRICS source 定义精确 + value 12 items 精确；_COUNT_METRICS source 定义精确 + value 1 item；_SUCCESS_BOOL_METRICS source 定义精确 + value 1 item；get_git_provenance source 详尽（commit/dirty init/try/except/rev-parse HEAD command/status --porcelain command/cwd/capture_output/text/encoding/errors/timeout kwargs/returncode check/stdout.strip()/dirty bool assignment/return dict 共 18+ token）；get_dependency_versions source 详尽（lazy import importlib.metadata/versions init/for pkg loop/version call/PackageNotFoundError catch/Exception catch/return versions/no subprocess）；build_provenance source 详尽（9 keys in order：report_version/evaluator_version/generated_at/git/git_diff_summary/dependency_versions/python_version/os/max_chars，int(max_chars)，datetime.now().astimezone().isoformat()）；build_devset_section source 详尽（6 keys in order：devset_status/file_count/content_group_count/pdf_count/docx_count/categories_covered，no subprocess/datetime）；aggregate_summary source 详尽（4 buckets：counts 求和/success_rates 算 rate/ratio 各项 macro average/silent_drop 求和；不混合出综合分数）；__all__ 5 entries 精确顺序（get_git_provenance/get_dependency_versions/build_provenance/build_devset_section/aggregate_summary）；namespace 完整（5 helpers + 3 constants + EVALUATOR_VERSION/REPORT_VERSION/subprocess/datetime/Path/Any 都在；不含 json/os/logging/threading/asyncio）；模块 source 不含 print/logging/async/threading/os/concurrent.futures/numpy/pandas/json import/load_manifest/process_single/compute_automatic_metrics；get_dependency_versions 行为（返回 3 keys：pdfplumber/python-docx→pdfplumber/python_docx/kreuzberg；PackageNotFoundError 不暴露）；build_provenance 行为（返回 9 keys in order；max_chars=int；commit short sha 7 chars）；aggregate_summary 行为（返回 4 keys in order：counts/success_rates/ratio_avgs/silent_drop；空 list 默认零值；不混合类型）；helper metadata（5 functions FunctionType；__module__ == 'evaluation.report'；qualname 精确）；签名 introspection（get_git_provenance 0 params；get_dependency_versions 0 params；build_provenance 1 param name max_chars；build_devset_section 1 param name manifest；aggregate_summary 1 param name reports；no var args/kwargs）；docstring 含 provenance/devset/summary/per_doc/4 categories/不混合类型；不缓存验证（重复调用得新 dict）

### 改动
- 新增 `tests/test_evaluation_report_edges19.py`（149 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **模块 imports 精确**：5 import 语句精确字符串；import 顺序 __future__→subprocess→datetime→pathlib→typing
- **常量精确**：_RATIO_METRICS 12 items tuple；_COUNT_METRICS 1 item；_SUCCESS_BOOL_METRICS 1 item；source 定义精确（'(' / ')' / 元素逐项）
- **get_git_provenance source**：所有 18+ 关键 token 精确（commit='' init / dirty=False init / try: / except Exception: / 'git' 'rev-parse' 'HEAD' / 'git' 'status' '--porcelain' / subprocess.run / cwd / capture_output=True / text=True / encoding='utf-8' / errors='replace' / timeout / .returncode / stdout.strip() / dirty = bool(...) / return {...}）
- **get_dependency_versions source**：所有关键 token 精确（lazy import importlib.metadata 在函数内 / versions = {} / for pkg in (...) / version(pkg) / except PackageNotFoundError / except Exception / return versions）；不含 subprocess
- **build_provenance source**：9 keys 顺序精确（report_version/evaluator_version/generated_at/git/git_diff_summary/dependency_versions/python_version/os/max_chars）；'int(max_chars)'；'datetime.now().astimezone().isoformat()'
- **build_devset_section source**：6 keys 顺序精确（devset_status/file_count/content_group_count/pdf_count/docx_count/categories_covered）；不含 subprocess/datetime
- **aggregate_summary source**：4 buckets 详尽（'counts'：求和 / 'success_rates'：rate / 'ratio_avgs'：macro average / 'silent_drop'：求和；不混合出综合分数）
- **__all__**：5 entries 精确顺序 ['get_git_provenance', 'get_dependency_versions', 'build_provenance', 'build_devset_section', 'aggregate_summary']
- **namespace**：5 helpers + 3 constants（_RATIO_METRICS/_COUNT_METRICS/_SUCCESS_BOOL_METRICS）+ EVALUATOR_VERSION/REPORT_VERSION/subprocess/datetime/Path/Any 都在；不含 json/os/logging/threading/asyncio
- **不含禁止内容**：print/logging/subprocess（仅 get_git_provenance 用）/async/threading/json/concurrent.futures/numpy/pandas/load_manifest/process_single/compute_automatic_metrics 都不在 source 中（部分除外已精确说明）
- **get_dependency_versions 行为**：返回 3 keys（pdfplumber/python_docx/kreuzberg）；PackageNotFoundError 不在返回 dict
- **build_provenance 行为**：返回 9 keys in order；max_chars int；'git' key 来自 get_git_provenance；'commit' 7 chars short sha
- **aggregate_summary 行为**：返回 4 keys in order；空 list 默认零值（counts/success_rates/ratio_avgs/silent_drop）；不混合类型
- **helper metadata**：5 functions 都是 FunctionType；__module__ == 'evaluation.report'；__qualname__ 精确
- **签名 introspection**：get_git_provenance 0 params；get_dependency_versions 0 params；build_provenance 1 param name max_chars；build_devset_section 1 param name manifest；aggregate_summary 1 param name reports；5 functions 都 no var args/kwargs
- **docstring**：含 provenance/devset/summary/per_doc/4 categories/不混合类型
- **不缓存验证**：get_git_provenance 重复调用得新 dict；get_dependency_versions 重复调用得新 dict

### 撞墙记录
- 0 fail 首次跑（149 全通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 278 后）：25613 pass / 0 fail / 16 skip（HEAD `582494c`）

### 下一步建议
- 候选：
  - evaluation/* 第二十轮（饱和区域，覆盖 source-level 不变量深化）
  - 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）
  - 候选 K（schema 加严）仍在范围内

**建议**：评估 saturation。evaluation/* 已达 edges18-19，进一步 edges 边际收益低。可转向 K（schema 加严）或 docs 之外的轻量深化。

---

## Round 279 — evaluation/runner.py 第二十轮（102 测试）

### 目标
- 给 `evaluation/runner.py`（228 行）加第二十轮 edges 测试，覆盖 edges19 未触及的角度：**schema 交叉验证**（run_evaluation 实际输出通过 evaluation-report.schema.json，含空 manifest / 单失败 doc / expected_failure / 组合 4 种场景）；**失败文档路径**（DocumentEntry 指向不存在文件 → process_single 返 file_not_found → 12 个 null-prone metrics 全部 null+pipeline_failed；element_count_by_type 也 null+pipeline_failed；error_code.value=='file_not_found'；wall_time 5 keys；total 非 null>=0）；**expected_failures 完整路径**（matches=True/False；字段顺序；多 ef 独立）；**多文档 manifest**（per_doc 长度匹配；summary success_count=0/total=N/rate=0.0；counts participating_docs=0/sum=None；silent_drop_total=None）；**tolerance_chars 传播**（默认 30；KEYWORD_ONLY）；**_annotation_present 行为**（public per_doc 不含 _ 前缀字段；4 keys 精确）；**provenance 字段类型**（9 keys 精确；max_chars 是 int 不是 bool；dependencies 是 dict；parser_name 非空 str；parser_version 在所有失败时 None；evaluator_version/report_version 非 空 str；run_timestamp_iso 非空 str；git_dirty 是 bool；git_commit str-or-None）；**summary 4 buckets 字段类型**（counts/success_rates/ratio_macro_averages 都是 dict；silent_drop_total 是 None-or-int；counts.element_count_total 含 sum+participating_docs；success_rates.pipeline_success 含 success_count+total+rate；ratio_macro_averages 12 项；每项含 macro_average+participating_docs+not_evaluated；空 manifest 全 None/0）；**devset 字段**（6 keys 精确；status enum；file_count int；categories_covered list）；**不修改 manifest**（documents/expected_failures/project_root/devset_status 都不变）；**out_stub 清理**（_per_doc/<doc_id>.json 失败后不留盘）；**写盘后报告 schema 通过 + 无 \u 转义**；**report top-level 字段类型**（6 keys 都是 dict/list 正确类型）；**module source 不含 subprocess/os/logging/concurrent.futures/asyncio/threading**；**__all__ 仍是 ['run_evaluation']**；**_process_one 5-tuple 类型**（失败时 (None, dict, float, None, None)）；**out_stub 失败时被清理；_per_doc 目录被创建**；**_load_annotation 行为补充**（目录→None；None→None；嵌套 dict；非 UTF-8 字节抛 UnicodeDecodeError 不被 catch；source 仅 catch (OSError, json.JSONDecodeError) 不含通用 except）；**devset_status 传播**（complete/incomplete 都能传到 report）；**per_doc source_type/doc_id 传播**；**parser_name/max_chars 默认值与传播**；**14 metrics key 集合 + 6 annotation_metrics key**；**write_json=False 行为**（outputs/ 下不写 per-doc JSON）；**output_path 在嵌套子目录下也能创建并写盘**

### 改动
- 新增 `tests/test_evaluation_runner_edges20.py`（102 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **schema 交叉验证**：4 种 manifest 场景（空 / 失败 / expected_failure / 组合）的 report 都通过 evaluation-report.schema.json
- **失败文档路径**：file_not_found 错误码正确传播到 metrics.error_code.value；12 null-prone metrics 全部 null+pipeline_failed
- **expected_failures**：matches True/False 都验证；字段顺序精确；多 ef 独立记录
- **多文档 manifest**：per_doc 长度匹配；summary 数值正确聚合
- **tolerance_chars**：默认 30；KEYWORD_ONLY；自定义值不报错
- **provenance**：9 keys 精确集合；6 字段类型严格（int/dict/str/bool/None 等）
- **summary 4 buckets**：keys 精确；空 manifest 全部 None/0 默认值
- **devset**：6 keys 精确；status enum；数值字段是 int；list 字段是 list
- **不修改 manifest**：4 个核心字段引用/值都不变
- **out_stub 清理**：失败/expected_failure 跑完 _per_doc/<doc_id>.json 都被 unlink
- **写盘后报告 schema 通过**：从磁盘读回再 schema validate 通过
- **module source 禁止内容**：runner.py 不直接用 subprocess/os/logging/concurrent.futures/asyncio/threading
- **__all__**：仍只是 ['run_evaluation']
- **_process_one 5-tuple 类型**：失败时 (None, dict, float, None, None)；total>=0；out_stub 被清理；_per_doc 被创建
- **_load_annotation 行为**：目录/None 都返 None；嵌套 dict 加载成功；非 UTF-8 抛 UnicodeDecodeError 不被 catch；source 仅 catch (OSError, json.JSONDecodeError) 不含通用 except
- **devset/per_doc 传播**：devset_status/source_type/doc_id/parser_name/max_chars 都从输入正确传播
- **14 metrics key + 6 annotation_metrics key**：失败 doc 的 metrics 含全部预期 keys
- **write_json=False**：outputs/ 下不写 per-doc JSON
- **嵌套子目录**：output_path 在 deep/nested/subdir/ 下也能创建

### 撞墙记录
- 1 fail 首次跑（已修复）：
  - test_load_annotation_returns_none_for_broken_utf8：UnicodeDecodeError 不是 OSError 子类（属 ValueError），_load_annotation 的 except 不捕获；改为 test_load_annotation_broken_utf8_raises_unicode_decode_error，验证 raises UnicodeDecodeError；并新增 test_load_annotation_only_catches_oserror_and_jsondecodeerror 验证 source 不含通用 except
- 1 syntax error 首次跑（已修复）：
  - test_run_evaluation_written_report_no_u_escape_failing 的 docstring 含 '\u' 被 Python 解释为 unicode escape；改为 r""" raw string"""

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 279 后）：25715 pass / 0 fail / 16 skip（HEAD `d0539f8`）

### 下一步建议
- 候选：
  - evaluation/* 第二十一轮（schema 联动深化，新角度）
  - evaluation/annotation_metrics.py 第十九轮（与 metrics.py 看齐）
  - evaluation/metrics.py 第十九轮
  - 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：edges20 schema 联动模式可推广到其他模块（report/manifest/metrics 都可以做 schema 交叉验证）。下一轮选 evaluation/annotation_metrics.py 第十九轮，借鉴 edges20 的"实际行为+schema 验证"组合，加新角度（chunk_boundary_prf 多分支组合验证）。

---

## Round 280 — evaluation/annotation_metrics.py 第十九轮（104 测试）

### 目标
- 给 `evaluation/annotation_metrics.py`（195 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：**chunk_boundary_prf position 分支**（"before" 走 find_pos；"after"/unknown 走 find_pos + len(marker)）；**完美匹配**（2 chunks + 2 anchors 全在容差内 → P/R/F1=1.0）；**部分匹配**（anchors 多于预测 → recall<1.0；预测多于 anchor → precision<1.0）；**tolerance_chars 边界值**（=0 必须精确；=1 含距离 1；刚好 d==tolerance 算匹配；d>tolerance 不算；tolerance 大就宽松）；**missing_markers 行为**（marker 不在 stream → 加入；空 marker 也加入；list 类型；全找到则无 _missing_markers 字段）；**重复 marker**（search_from 推进避免都命中第 1 次）；**f1=0 when p=r=0**（denom<=0 分支）；**f1 null when recall null**（gt_positions 空 → recall null → f1 null）；**_tolerance_chars 始终在输出**（5 种路径都验证：document_none/annotation_falsy/no_predicted/no_anchors/normal）；**一对一贪心匹配**（按距离排序；用具体 case 验证 pred 不能同时匹配两个 anchor）；**marker 在 chunk 文本内部**（不影响 find）；**最后 chunk 不算边界**（i == len-1 break）；**source-level 关键 token**（30+ 验证：search_from=0 / pairs.sort / used_pred/used_gt set / list[tuple[int,int,int]] / abs(pv-gv) / pairs.append((d,pi,gi)) / used_pred.add(pi) / used_gt.add(gi) / search_from=find_pos+len(marker) / for pi,pv in enumerate(predicted) / for gi,gv in enumerate(gt_positions) / d <= tolerance_chars / p_val/r_val None 检查 / denom <= 0 / 2 * p_val * r_val / denom / position == "before" / find_pos < 0 / stream.find(marker, search_from) / i == len(norm_chunks) - 1 / pos += len(txt) + 1 / stream.find(txt, pos) / pos = end + 1 / c.get("text") or "" / a.get("marker", "") / a.get("position", "after") / missing_markers.append(marker) / gt_positions.append(find_pos) / gt_positions.append(find_pos + len(marker)) / predicted.append(end) / end = find_pos + len(txt)）；**不修改输入**（document/annotation）；**figure_caption_prf 各种输入都返固定 null**（document dict/None/empty；annotation dict/None/empty；不读 document/annotation 字段）；**模块 source 不含 json/print/logging/subprocess/asyncio/threading/os/pathlib/concurrent**；**__all__ 3 entries 顺序精确**；**PARSER_DOES_NOT_EMIT_RELATIONS 常量值/snake_case**；**_null/_ratio 来自 evaluation.metrics**；**normalize_text 来自 app.chunkers.structural**；**3 次调用独立 + 修改输出不影响下次**；**falsy annotation**（{}/None）→ no_annotation；**chunks key 缺失/空 list/单元素** → no_predicted_boundaries；**chunks>=2 + anchors=[]** → no_ground_truth_anchors

### 改动
- 新增 `tests/test_annotation_metrics_edges19.py`（104 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **chunk_boundary_prf position 分支**：before/after/unknown 三种都验证
- **完美/部分匹配**：2v2 全匹配 P/R/F1=1.0；2v1 recall=0.5；1v2 precision=0.5
- **tolerance_chars 边界值**：0 / 1 / 大值都验证；d==tolerance 算匹配；d>tolerance 不算
- **missing_markers**：marker 不在 stream / 空 marker 都加入；list 类型；全找到则无字段
- **重复 marker**：search_from 推进验证
- **f1 边界**：p=r=0 → f1=0.0；r_val=None → f1 null
- **_tolerance_chars 5 路径**：document_none/annotation_falsy/no_predicted/no_anchors/normal 都有
- **一对一贪心**：用 marker='a' 和 marker='b' 验证 pred 不能同时匹配两个 anchor
- **marker 在 chunk 内部**：find 仍能工作
- **最后 chunk 不算边界**：i==len-1 break
- **source-level**：30+ token 精确验证（含算法关键步骤）
- **不修改输入**：document/anchor 内容不变
- **figure_caption_prf**：5 种输入组合都返固定 null；不读字段
- **模块禁止内容**：json/print/logging/subprocess/asyncio/threading/os/pathlib/concurrent 都不在 source
- **__all__**：3 entries 顺序精确 [PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf]
- **PARSER_DOES_NOT_EMIT_RELATIONS**：值精确 'parser_does_not_emit_relations'；snake_case；模块身份相同
- **_null/_ratio/normalize_text 跨模块引用**：模块 namespace 中的引用是 evaluation.metrics._null/_ratio 和 app.chunkers.structural.normalize_text 的同一对象
- **多次调用独立**：3 次调用结果相等但 dict 不同；修改输出不影响下次
- **falsy/chunks 缺失/空 list/单元素**：分支都覆盖

### 撞墙记录
- 2 fail 首次跑（已修复）：
  - test_chunk_boundary_prf_f1_null_when_precision_null：实际 chunks=[{text:""},{text:""}] 时 stream=""，但 stream.find("", 0)=0（空字符串 find 返 0），所以 predicted=[0]，num_pred=1，precision=_ratio(0.0)（value=0.0 非 None）；改为 test_chunk_boundary_prf_f1_null_when_recall_null，验证 recall null → f1 null
  - test_chunk_boundary_prf_one_to_one_prevents_double_match：原 markers 'a' 和 'ab'，但 'ab' 从 search_from=1 找不到（'ab' 在 'ab cd' 中只出现一次，位置 0），加入 missing_markers；改为 markers 'a' 和 'b'（'b' 在 search_from=1 处可找到，位置 1）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 280 后）：25819 pass / 0 fail / 16 skip（HEAD `5707bb4`）

### 下一步建议
- 候选：
  - evaluation/metrics.py 第十九轮（与 annotation_metrics 看齐）
  - evaluation/schema.py 第十三轮（最浅的 evaluation 模块）
  - 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：edges19 schema 联动模式可继续推广。下一轮选 evaluation/metrics.py 第十九轮（169 测试基础），加 schema 交叉验证 + 多分支组合新角度。

---

## Round 281 — evaluation/metrics.py 第十九轮（168 测试）

### 目标
- 给 `evaluation/metrics.py`（382 行）加第十九轮 edges 测试，覆盖 edges18 未触及的角度：**compute_automatic_metrics 失败场景**（document=None + error=dict → pipeline_success.value=False 不是 None；error_code.value=error['code']；schema_valid null+pipeline_failed；12 null-prone metrics 都 null+pipeline_failed；element_count_by_type 也 null+pipeline_failed）；**成功场景**（pipeline_success=True；error_code.value=None；element_count_total=int_metric(len(elements))；element_count_by_type 是 dict；多 type 计数）；**source_type 分支**（pdf 触发 _pdf_locator_ratio + docx null+not_pdf_document；docx 触发 _docx_locator_ratio + pdf null；unknown 两边都 null）；**_pdf_locator_ratio 详细边界**（0 elements→null；1 valid paragraph+bbox→1.0；page=0/-1/1.5/'1'/None invalid；bool page 实际通过 int 检查；text type 缺 bbox invalid；table/header/footer 不需要 bbox；mixed valid/invalid 比例；source_locator 缺失或 None）；**_docx_locator_ratio 详细边界**（7 个 structural_key 单独验证：section/paragraph_index/run_index/table_index/row_index/col_index/relationship_id；含 page 或 bbox→invalid；无 structural_key→invalid；mixed）；**_is_valid_bbox 详细边界**（not list/tuple/None/short/long 全 False；bool 元素 False；str/None/nan/inf/-inf 元素 False；4 ints/floats/mixed True；zero box True；负坐标 True）；**_image_resource_ratio 详细边界**（无 image→null+no_image_elements；image 无 resource_path→0.0；resource_path=''→0.0；存在文件→1.0；不存在→0.0；0 字节文件→0.0；image_base_dir fallback 拼接；mixed）；**_chunk_reference_ratio 详细边界**（无 chunks→null；all valid；all invalid；空 ids 不算 valid；ids=None 不算；缺 key 不算；mixed；部分有效部分无效 in 一个 chunk→不算）；**_strip_unicode_whitespace 字符级**（ASCII space/tab/newline/CR；NBSP/em space/en space/ideographic space/line separator/paragraph separator 都删；空字符串/纯空白/无空白；保留标点中文 emoji；不排序）；**_text_preservation 详细边界**（都空→null+empty_expected_and_actual；identical→1.0；image 不参与；缺字符/多字符；empty_actual/empty_expected；Counter 交集 min 语义；空白忽略；3 keys 返回；每 metric 是 dict 含 value+reason）；**_heading_boundary_ratio 详细边界**（无 heading→null+no_heading_elements；完美匹配 1.0；无匹配 0.0；partial；空 ids 跳过；ids=None 跳过；只看 first id；多 chunk 都贡献 first id）；**_silent_drop_count 详细边界**（无 expectations→null；空 dict；无 element_count_by_type key；element_count_by_type 空；actual>=exp→0；actual<exp→差值；actual=0；expected type 不在 actual；多类型求和）；**_null/_ratio/_bool_metric/_int_metric 一致性**（_null value None/reason input/2 keys；_ratio value float/reason None/int 转 float；_bool_metric value bool/truthy/falsy；_int_metric value int 非 bool/float 转 int/str digit 转）；**compute_automatic_metrics 集成**（image_base_dir 给定 vs None；expectations 给定 with/without drops；expectations 但无 element_count_by_type）；**schema_valid 异常路径**（monkeypatch document_passes_schema 抛 RuntimeError → value=False + reason 含 schema_check_exception + RuntimeError）；**不修改 document elements/chunks/expectations**；**两次调用独立 + 修改输出不影响下次**；**__all__**；**namespace 完整性**（13 sub-helper + 3 常量 + math/Counter/Path/Any）；**模块 source 不含 re/uuid/random/time/datetime**；**14 个 helper 都是 FunctionType + module identity**；**子函数签名**（每个 helper 参数数 + 名字精确）；**常量精确**（_TEXT_TYPES 7 items / _PDF_BBOX_REQUIRED_TYPES 4 items / subset 关系 / image/table/header/footer 不在）

### 改动
- 新增 `tests/test_evaluation_metrics_edges19.py`（168 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **失败/成功场景**：pipeline_success.value False/True；error_code 取自 error 或 None；schema_valid 三种状态；12 null-prone metrics
- **source_type 分支**：pdf/docx/unknown 三种都验证
- **_pdf_locator_ratio**：15+ 边界场景（含 page type quirk: bool 是 int 子类）
- **_docx_locator_ratio**：7 个 structural_key + page/bbox 排除 + 无 key + mixed
- **_is_valid_bbox**：16 边界（list/tuple/None/short/long/bool/str/None/nan/inf/-inf/int/float/mixed/zero/negative）
- **_image_resource_ratio**：8 场景（无/有 resource_path/empty/exists/nonexistent/0-byte/fallback/mixed）
- **_chunk_reference_ratio**：8 场景（无/全 valid/全 invalid/空/None/缺 key/mixed/部分）
- **_strip_unicode_whitespace**：15 场景（ASCII/Unicode 各种空白；非空白保留；不排序）
- **_text_preservation**：11 场景（都空/identical/image 过滤/缺字符/多字符/empty_actual/empty_expected/Counter 交集/空白忽略/3 keys/dict 结构）
- **_heading_boundary_ratio**：8 场景（无/完美/无匹配/partial/空 ids/None/first id/multi chunk）
- **_silent_drop_count**：9 场景（无/空/无 key/空 element_count_by_type/>=/</=0/missing type/多类型求和）
- **helper 一致性**：_null/_ratio/_bool_metric/_int_metric 类型转换语义
- **集成场景**：image_base_dir/expectations with drops/expectations without drops
- **schema_valid 异常路径**：monkeypatch 验证 reason 含 schema_check_exception + RuntimeError
- **不修改输入**：elements/chunks/expectations 都不变
- **两次调用独立**：dict 不同；修改不影响下次
- **__all__ + namespace**：精确
- **模块禁止内容**：re/uuid/random/time/datetime 都不在
- **14 个 helper FunctionType + module identity**：所有 helper 都是函数且模块身份正确
- **子函数签名**：参数数 + 名字精确
- **常量精确**：3 常量值 + subset 关系

### 撞墙记录
- 0 fail 首次跑（168 全通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 281 后）：25987 pass / 0 fail / 16 skip（HEAD `dadbf27`）

### 下一步建议
- 候选：
  - evaluation/manifest.py 第二十轮（与 leader 看齐）
  - evaluation/schema.py 第十三轮
  - evaluation/cli.py 第二十轮
  - 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：metrics.py edges19 已饱和（168 测试）。下一轮选 evaluation/manifest.py 第二十轮（169 测试基础），加 schema 交叉验证 + DocumentEntry/ExpectedFailure 多场景。

---

## Round 282 — evaluation/manifest.py 第二十轮（118 测试）

### 目标
- 给 `evaluation/manifest.py`（239 行）加第二十轮 edges 测试，覆盖 edges19 未触及的角度：**load_manifest 完整文档场景**（empty documents；single/two documents；含 sha256/categories/paired_with/annotation_file/expectations 各种字段；含 expected_failures；expected_failure 含 source_type vs 不含；docx source_type；doc_id/path_str/resolved_path 传播；resolved_path 是绝对路径）；**load_manifest schema 失败场景**（缺 documents 键；documents 非 list；document 缺 doc_id/path/source_type；source_type 错 enum；额外字段；sha256 格式错；devset_status 错 enum；top-level 额外字段；expected_failure 缺 doc_id/path/expected_error_code）；**manifest_version 兼容性**（1.0 通过；2.0/1.1/非 str 都失败）；**JSON 解析失败**（invalid/empty/top-level-array 都抛 ManifestError 或 EvalSchemaError）；**DocumentEntry/ExpectedFailure/Manifest frozen**（setattr/delattr raises FrozenInstanceError；eq 相同值；hashable；可作 set 元素）；**Manifest properties 多场景**（file_count 0/1/N；pdf_count when no pdf；docx_count when no docx；categories_covered empty/merged/dedup/list 类型；content_group_count 0/unpaired/paired-bidirectional/paired-unidirectional/mixed）；**_is_absolute_like 字符级**（'/' / 'C:/' / 'C:\\' / lowercase drive / 'D:foo' 不 abs / relative / filename / empty / dot / double-dot；返回 bool）；**_has_backslash 字符级**（forward only / with backslash / mixed / just backslash / empty / no path；返回 bool）；**_resolve_relative_path 多场景**（normal/unicode/spaces/multi-slash/path escape/just filename/subdir；错误信息含字段名）；**_detect_project_root**（找 pyproject.toml；向上找父；找不到 fallback；输入是文件取 parent）；**模块 source 不含禁止 imports**（os/sys/logging/subprocess/asyncio/threading/concurrent/time/re）；**ManifestError 语义**（caught as Exception；str 含 message；no_args 也可；不接 errors kwarg）；**dataclass 类型 + field 数**（DocumentEntry 10 / ExpectedFailure 5 / Manifest 5）；**__all__ 5 entries 精确顺序**；**load_manifest 不修改磁盘文件**；**两次调用独立**；**project_root 默认 vs 显式**（None→detect；explicit 覆盖）

### 改动
- 新增 `tests/test_evaluation_manifest_edges20.py`（118 测试）
- 仅测试，不动业务代码

### 覆盖要点
- **load_manifest 多场景**：13 场景（empty/single/two/sha256/categories/paired/annotation/expectations/expected_failures/ef_source_type/ef_no_source_type/docx_source_type/doc_id/path_str/resolved_path）
- **schema 失败**：13 场景（缺 documents/documents 非 list/缺 doc_id/path/source_type/错 source_type/额外字段/sha256 格式/错 devset_status/top-level 额外/expected_failure 缺 doc_id/path/code）
- **manifest_version**：4 场景（1.0 通过；2.0/1.1/非 str 失败）
- **JSON 解析**：3 场景（invalid/empty/top-level array）
- **frozen dataclass**：DocumentEntry/ExpectedFailure/Manifest 都验 setattr/delattr/eq/hash/set
- **Manifest properties**：file_count/pdf_count/docx_count/categories_covered/content_group_count 多场景（含 paired 双向/单向/mixed）
- **_is_absolute_like**：12 字符级场景
- **_has_backslash**：7 字符级场景
- **_resolve_relative_path**：8 场景（含 path traversal 防护）
- **_detect_project_root**：4 场景（find pyproject/find parent/no pyproject fallback/file input）
- **模块禁止 imports**：os/sys/logging/subprocess/asyncio/threading/concurrent/time/re 都不在
- **ManifestError 语义**：caught as Exception；str 含 message；no_args 可；不接 errors kwarg
- **dataclass field count**：DocumentEntry 10 / ExpectedFailure 5 / Manifest 5
- **__all__ 5 entries 精确顺序**
- **不修改磁盘文件**：load_manifest 不动 manifest.json
- **两次调用独立**：不同 Manifest 对象，相等
- **project_root**：默认 detect vs 显式 override

### 撞墙记录
- 0 fail 首次跑（118 全通过）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 282 后）：26105 pass / 0 fail / 16 skip（HEAD `dcfc1a5`）

### 下一步建议
- 候选：
  - evaluation/cli.py 第二十轮（243 行）
  - evaluation/schema.py 第十三轮（80 行）
  - evaluation/report.py 第二十轮（200 行）
  - 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：edges20 schema 联动模式持续推广。下一轮选 evaluation/cli.py 第二十轮，加 schema 联动 + argparse 子命令深度场景。

---
