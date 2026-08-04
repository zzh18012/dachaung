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
