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

