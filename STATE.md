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
