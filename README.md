# dachaung

面向 KVFS 的复合文档解析与结构-语义分块原型。

**当前阶段（最小闭环）**：PDF/DOCX → 统一文档模型 → 基础结构分块 → JSON Schema 校验 → JSON 输出。

> 本阶段明确**不做**：Web UI、真实 KVFS 接入、向量化 / Sentence-BERT、OCR、cpp-chunker、内核代码、流式处理。

---

## 1. 环境

| 项目 | 值 |
|---|---|
| 操作系统 | Windows 11（Git Bash / msys2 ucrt64） |
| Python | CPython 3.12.10（**官方构建**，路径见下方命令） |
| 包管理 | uv（已有 0.11.11） |
| 工作目录 | `C:\Users\zzhn2\Desktop\dachuang-code` |

**禁止**使用 PATH 里的 mingw Python 3.14：uv 会拒绝（`Unknown operating system: mingw_x86_64_ucrt_gnu`），且主流库几乎没有 mingw wheel。

---

## 2. 安装（一次性）

```bash
# 在 Git Bash 中（用 Unix 路径风格）
cd "/c/Users/zzhn2/Desktop/dachuang-code"

# 用项目内指定的官方 Python 3.12.10 创建 .venv 并装齐依赖
uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"
```

**实测输出（2026-08-03）**：

```
Resolved 24 packages in 1m 24s
...
Installed 10 packages in 125ms
 + pdfminer-six==20260107
 + pdfplumber==0.11.10
 + pillow==12.3.0
 + python-docx==1.2.0
 ...
```

锁文件：`uv.lock`（已包含精确版本，要提交到 git）。

依赖（`pyproject.toml` 锁定范围）：

- `jsonschema>=4.21,<5` — JSON Schema 校验
- `kreuzberg>=4.10,<5` — 主解析器（实测能力受限，见第 7 节）
- `pdfplumber>=0.11,<0.12` — PDF 降级解析
- `python-docx>=1.2,<2` — DOCX 降级解析
- `pytest>=8.0,<9` — 测试（dev 组）

---

## 3. 运行

**所有命令都用项目内 venv 的 python，永远不直接敲 `python`**。

### 3.1 解析 PDF / DOCX → JSON

```bash
# 默认走 fallback parser（pdfplumber + python-docx），推荐
.venv/Scripts/python.exe -m app.cli parse samples/private/sample.pdf -o outputs/sample.json

# 切换到 kreuzberg parser（已知给出的是启发式 elements，会带 warning）
.venv/Scripts/python.exe -m app.cli parse samples/private/sample.docx -o outputs/sample.json --parser kreuzberg

# 自定义分块大小
.venv/Scripts/python.exe -m app.cli parse samples/private/sample.pdf -o outputs/sample.json --max-chars 1200
```

成功输出示例：

```
[OK] samples/private/sample.pdf → outputs/sample.json  (elements=18, chunks=13, warnings=0)
```

退出码：成功 `0`，失败 `1` 或 `2`。

### 3.2 仅校验已有的 JSON（独立子命令，不会把 JSON 当成 PDF/DOCX 输入）

```bash
.venv/Scripts/python.exe -m app.cli validate outputs/sample.json
```

成功：`[OK] ... 通过 Schema 校验`，退出码 0。
失败：`[FAIL] ...`，退出码 1。
文件不存在：`[ERROR] ...`，退出码 2。

### 3.3 单文件失败的结构化错误

CLI 不会崩溃，会输出结构化 JSON 到 stderr 并返回非零：

```json
{
  "schema_version": "0.1.0",
  "input": "samples/private/nope.pdf",
  "errors": [
    {"code": "file_not_found", "message": "输入文件不存在: ..."}
  ]
}
```

**失败时不残留半成品 JSON**（CLI 会主动清理）。

---

## 4. 输出格式（简化示例）

完整 Schema 见 `schemas/document.schema.json`。简化示例：

```json
{
  "schema_version": "0.1.0",
  "document_id": "doc-a1b2c3d4e5f60718",
  "source_path": "samples/private/sample.docx",
  "source_type": "docx",
  "source_hash": "a1b2c3d4...64位SHA-256...00112233",
  "parser_name": "fallback",
  "parser_version": "pdfplumber=0.11.10,python-docx=1.2.0",
  "elements": [
    {
      "element_id": "doc-a1b2c3d4e5f60718::e0000",
      "type": "heading",
      "content": "Chapter 1",
      "parent_id": null,
      "source_locator": {"paragraph_index": 0, "section": 0},
      "confidence": 0.95,
      "metadata": {"level": 1, "style": "Heading 1", "empty": false}
    },
    {
      "element_id": "doc-a1b2c3d4e5f60718::e0001",
      "type": "paragraph",
      "content": "Hello world.",
      "parent_id": null,
      "source_locator": {"paragraph_index": 1, "section": 0},
      "confidence": 0.95,
      "metadata": {"level": 0, "style": "Normal", "empty": false}
    }
  ],
  "chunks": [
    {
      "chunk_id": "doc-a1b2c3d4e5f60718::c0000",
      "text": "Chapter 1 Hello world.",
      "source_element_ids": ["doc-a1b2c3d4e5f60718::e0000", "doc-a1b2c3d4e5f60718::e0001"],
      "metadata": {"strategy": "sequential", "max_chars": 800, "char_count": 18}
    }
  ],
  "relations": [],
  "warnings": [],
  "errors": [],
  "metadata": {"fallback": true}
}
```

**关键字段说明**：

- `source_hash`：SHA-256 hex（小写 64 字符），用于去重和追溯
- `source_locator`（PDF）：必须含 `page`（≥1），可选 `bbox`（4 元数组）
- `source_locator`（DOCX）：含 `paragraph_index` 或 `table_index`、`section`，**没有 page/bbox**（DOCX 本身就没有稳定页码）
- 每个 `chunk` 必须有非空 `source_element_ids`，确保可追溯到原始 element

---

## 5. 测试

```bash
# 全部测试
.venv/Scripts/python.exe -m pytest

# 带详细输出
.venv/Scripts/python.exe -m pytest -v

# 只跑分块器
.venv/Scripts/python.exe -m pytest tests/test_chunker.py -v
```

**实测结果（2026-08-03）**：`54 passed, 6 skipped in 1.80s`

6 个 SKIPPED 是因为 `samples/private/` 没放真实样例（按设计 SKIPPED，不伪造）：

```
SKIPPED [1] samples/private/sample.pdf 未提供
SKIPPED [1] samples/private/sample.docx 未提供
SKIPPED [4] 同上（不同 parser 的参数化测试）
```

测试覆盖：

- `test_models.py`：dataclass 字段、必填项、序列化
- `test_schema.py`：合法 / 非法 JSON、PDF/DOCX locator 差异、content/resource_path 至少一个
- `test_parsers.py`：FallbackParser（合成 PDF/DOCX）、KreuzbergParser、ParserError 结构
- `test_chunker.py`：标题硬边界、table 独立 chunk、长度切分、**不丢不重**（统一规范化后拼接比较）、source_element_ids 非空
- `test_pipeline_integration.py`：合成样例端到端、CLI 子进程、校验-前-不写盘、真实样例（可选 SKIPPED）

---

## 6. 测试样例

把**无隐私**的样例放进 `samples/private/`（此目录被 `.gitignore` 忽略，不会上传 GitHub）：

- `samples/private/sample.pdf` — 任意电子版（非扫描）PDF，例如公开论文、课程笔记导出
- `samples/private/sample.docx` — 任意 DOCX

放好后重跑 `pytest`，原 SKIPPED 的测试会自动跑。

**禁止**：含个人信息的文件（如申请书）、网络下载的不明文件。

---

## 7. Kreuzberg 实测结果（2026-08-03，kreuzberg==4.10.2）

按你的要求"安装成功不等于功能满足要求，必须分别验证"，实测如下：

| 场景 | 结果 |
|---|---|
| `pip install kreuzberg==4.10.2` | ✅ 装好 |
| `import kreuzberg` | ✅ 通过 |
| 对 plain text 提取 | ✅ 返回 content + metadata |
| 对 DOCX 调用 `extract_file_sync` | ⚠️ 返回 content + tables + metadata，**elements 字段为空**（即使开 `include_document_structure=True`） |
| 对手写最小 PDF 调用 | ⚠️ 返回 content，elements/pages/tables 全空 |
| 对 DOCX 给 paragraph_index | ❌ 给不出 |
| 对 PDF 给 page/bbox | ❌ 给不出（page_number=0 是无效占位） |

**结论**：Kreuzberg 4.10.2 的强项是整篇 OCR 和表格，但**给不出元素级 source_locator**。我们的 schema 要求每个 element 有 page/bbox 或 paragraph_index，所以 **默认走 `fallback` parser**。Kreuzberg 适配器仍保留（未来版本可能升级支持）。

降级链路：

```
pipeline → Parser 接口
            ├─ FallbackParser（默认，pdfplumber + python-docx）
            └─ KreuzbergParser（可选，--parser kreuzberg）
                              └─ 解析时记录 kreuzberg_no_structured_elements / kreuzberg_pdf_no_bbox warning
```

---

## 8. 常见错误

### 8.1 `Unknown operating system: mingw_x86_64_ucrt_gnu`

用了 PATH 里默认的 mingw Python 3.14。**解决**：永远用 `.venv/Scripts/python.exe`，不要直接敲 `python`。

### 8.2 `pdfplumber_open_failed: 'y0'`

之前版本的 bug，已修（pdfplumber 用 `top`/`bottom` 而非 `y0`/`y1`）。如果再遇到，提 issue。

### 8.3 `pdf_no_text_extracted` warning

PDF 可能是扫描件，本阶段**不做 OCR**。换成电子版 PDF，或等后续阶段加 OCR 支持。

### 8.4 `schema_validation_failed`

pipeline 在写盘前会先校验，如果失败说明数据模型有 bug。看 stderr 中的 `validation_errors` 数组定位。

### 8.5 中文乱码（CLI 子进程）

CLI 已强制 utf-8 输出。如果调用方还乱码，在子进程环境里加 `PYTHONIOENCODING=utf-8`。

### 8.6 真实样例测试 SKIPPED

按设计：`samples/private/sample.pdf` 或 `.docx` 不存在就 SKIP，不伪造通过。把样例放进去即可。

---

## 9. 目录结构

```
dachaung-code/
├── .gitignore
├── README.md
├── CLAUDE.md
├── pyproject.toml          # 项目元数据 + 依赖锁定范围
├── uv.lock                 # uv 自动生成的精确锁文件
├── app/
│   ├── __init__.py
│   ├── cli.py              # 命令行入口
│   ├── pipeline.py         # 串联 parse → chunk → validate → write
│   ├── models.py           # 统一文档模型 dataclass
│   ├── schema.py           # JSON Schema 加载与校验
│   ├── hash.py             # SHA-256
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py         # Parser 抽象接口
│   │   ├── kreuzberg_parser.py
│   │   └── fallback_parser.py  # pdfplumber + python-docx
│   └── chunkers/
│       ├── __init__.py
│       └── structural.py   # 标题硬边界 + 长度切分
├── schemas/
│   └── document.schema.json
├── tests/                  # 单元 + 集成测试
├── samples/
│   ├── README.md           # 告诉你该放什么
│   └── private/            # .gitignore；放真实样例（无隐私）
└── outputs/                # 输出 JSON，gitignore（.gitkeep 例外）
```

---

## 10. 后续阶段（不在本阶段范围）

- 真实 KVFS 接入
- 向量化 / Sentence-BERT / 语义检索
- OCR（Tesseract / PaddleOCR）
- 跨页段落重建
- Table Transformer 微调
- cpp-chunker 加速
- Web UI
