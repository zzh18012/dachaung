# CLAUDE.md（项目规则，给未来的 Claude 读）

## 项目目标（当前阶段）

构建"PDF/DOCX → 统一文档模型 → 基础结构分块 → Schema 校验 → JSON 输出"的最小闭环原型。

## 范围（本阶段明确不做）

- Web UI / 前端
- 真实 KVFS 接入（仅设计 `source_locator` 字段以便未来对齐）
- 向量化、Sentence-BERT、任何 embedding
- cpp-chunker / Rust 加速
- 多 OCR 引擎
- 内核代码 / FUSE / Docker / 数据库
- 流式处理 / 异步 / 多进程

## 环境

- 工作目录：`C:\Users\zzhn2\Desktop\dachuang-code`（已是 git 仓库，远程 `zzh18012/dachaung`）
- Python 解释器：`C:\Users\zzhn2\AppData\Local\Programs\Python\Python312\python.exe`（**官方 CPython 3.12.10**）
- 严禁使用 PATH 里的 mingw Python 3.14（uv 会拒绝，wheel 兼容性差）
- 虚拟环境：`.venv/Scripts/python.exe`
- 包管理：uv（已有 0.11.11）
- Shell：Git Bash（msys2 ucrt64），用 Unix 语法（`/c/...`、`/dev/null`）

## 常用命令

```bash
# 创建/同步虚拟环境
uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"

# 运行测试
.venv/Scripts/python.exe -m pytest

# 解析（PDF/DOCX 输入）—— 注意子命令 parse
.venv/Scripts/python.exe -m app.cli parse <input.pdf|input.docx> -o <output.json>

# 切换 parser（默认 fallback，因 kreuzberg 实测给不出 elements 结构）
.venv/Scripts/python.exe -m app.cli parse <input.docx> -o out.json --parser kreuzberg

# 仅校验已生成的 JSON（独立子命令，不要把 JSON 当成 PDF 输入）
.venv/Scripts/python.exe -m app.cli validate <output.json>
```

## Parser 选择策略

**默认走 `fallback`**（pdfplumber + python-docx）。

Kreuzberg 4.10.2 实测：
- 对 DOCX 调用 `extract_file_sync`，`elements` 字段始终为空（即使开 `include_document_structure=True`）
- 对手写最小 PDF，elements/pages/tables 全空
- 给不出 PDF 的 page/bbox，给不出 DOCX 的 paragraph_index

因此默认走 fallback，kreuzberg 适配器保留为可选路径（未来升级后可能启用）。
切换不会改业务代码，只改 CLI `--parser` 参数。

## 关键不变量

- Pipeline 在写盘前**必须**通过 JSON Schema 校验（schema.py validate）
- 单文件失败 → 结构化 errors JSON + 非零退出码，不崩溃
- 每个 chunk 必须有非空 source_element_ids
- PDF 与 DOCX 的 source_locator 结构不同（schema 用 if/then 区分）
- content 和 resource_path 至少有一个非 null（schema 用 anyOf 保证）
- "分块不丢不重"测试用 `normalize_text` 统一规则：所有空白压成单空格、strip 两端



## 禁止事项

- 不读取或复制 `C:\Users\zzhn2\Desktop\大创` 中的私人申请书
- 不在源码/测试/输出中硬编码私人文件绝对路径
- 不执行 `git commit` / `git push` 除非用户明确要求
- 不修改全局 Git 配置（`http.sslbackend=schannel` 已在 `.git/config` local 设置）
- 不使用 `sudo`（Windows 上无意义，Linux 上需用户确认）
- 不执行 `reset --hard` / `clean -fd` / `push --force` 等破坏性 Git 操作
- 不全局安装依赖（只用 `.venv`）
- 不安装系统级组件
- 不增加计划外的主要依赖（如需增加必须先询问用户）
- 不伪造测试结果

## 隐私约束

- 测试样例放在 `samples/private/`，已被 `.gitignore` 忽略
- 用户将手动放入：1 个无隐私 PDF + 1 个无隐私 DOCX
- 真实样例不存在时，相关测试应明确显示 SKIPPED 而非伪造通过

## SSL 配置来源

`http.sslbackend=schannel` 仅写在 `.git/config` 的 local 配置中，未污染 global。
原因：Git Bash 默认 OpenSSL 在该机器上访问 GitHub HTTPS 时会失败，切到 Schannel（用 Windows 系统证书）解决。
