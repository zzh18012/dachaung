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

可选依赖（不装则自动降级，不报错）：

- `tqdm` — 批量处理进度条（`python -m app.cli batch-parse`）。未安装或 stderr 非 TTY（CI）时降级为每文档一行文本进度（Stage 8 批次 16）。

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

### 3.4 结构化日志（`--log-file` / `--verbose`，Stage 8 批次 17）

`batch-parse` 与 `evaluation.cli run` 支持结构化 JSONL 日志（每行一个 JSON 对象）：

```bash
# 推荐写到 outputs/ 下（已 gitignored）
.venv/Scripts/python.exe -m app.cli batch-parse samples/private/devset \
    -o outputs/batch-out --log-file outputs/batch.jsonl

# 同时打到 stderr（与进度输出可能交错，建议用 --log-file 获得干净日志）
.venv/Scripts/python.exe -m evaluation.cli run \
    --manifest samples/private/devset/manifest.json --output outputs/eval.json \
    --log-file outputs/eval.jsonl --verbose
```

事件类型：`batch_start` / `file_complete` / `file_warning` / `file_error`（含
`traceback`）/ `batch_complete`；评测侧 `eval_start` / `doc_complete` /
`doc_error` / `eval_complete`。默认（不带参数）零输出变化。

注意事项：

- **append 模式**：日志只追加不覆盖，需定期手动清理（无自动轮转）。
- `timestamp` 为 epoch 秒，转 ISO：

```python
import datetime
datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()
```

- 完整性校验（首尾事件 + 逐文档事件数 == 文档总数）：

```bash
.venv/Scripts/python.exe scripts/verify_batch17_log_completeness.py \
    --log outputs/batch.jsonl --kind batch
```

### 3.5 Parser 注册表与插件（Stage 8 批次 18）

```bash
# 列出已注册 parser（含插件）
.venv/Scripts/python.exe -m app.cli list-parsers

# 按扩展名自动发现（priority 小者优先；显式 --parser 永远覆盖发现）
.venv/Scripts/python.exe -m app.cli parse doc.md -o out.json --parser auto
```

内置参考插件 `markdown_enhanced`（priority 5）：YAML frontmatter 受限解析
（仅扁平 `key: scalar`，嵌套/列表记 warning 跳过，不伪装完整 YAML）+
GFM 任务列表（`- [ ]` / `- [x]` → `metadata.task_item` / `metadata.checked`）。

**外部插件开发指南**：写一个继承 `app.parsers.base.Parser` 的类（实现
`parse(path, source_hash) -> Document`，声明 `name` / `version` /
`supported_extensions` / `priority`），在自己的模块里 import 后用装饰器注册：

```python
from app.parser_registry import register
from app.parsers.base import Parser

@register
class MyParser(Parser):
    name = "my_parser"
    version = "1.0.0"
    supported_extensions = (".myx",)
    priority = 100

    def parse(self, path, source_hash):
        ...
```

然后 `import` 该模块即可被 `list-parsers` / `--parser auto` 发现。
`discover_parser(path)` 返回 parser **名称**（`str`，非实例）——实例化
统一走 `get_parser(name)`，`image_output_dir` 等构造参数在该层注入。
不做 entry_points 自动扫描（显式优于隐式）；重名注册在 import 时即报
ValueError。完整 YAML（PyYAML）支持见 docs/BACKLOG.md。

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
├── docs/
│   └── evaluation.md       # Stage 2 评测方法与基线
├── pyproject.toml          # 项目元数据 + 依赖锁定范围
├── uv.lock                 # uv 自动生成的精确锁文件
├── app/
│   ├── __init__.py
│   ├── cli.py              # 命令行入口（parse / validate）
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
├── evaluation/             # Stage 2 评测包（不改 parser/chunker）
│   ├── cli.py              # run / validate-report 子命令
│   ├── manifest.py         # 清单加载 + 路径校验
│   ├── metrics.py          # 13 项自动指标
│   ├── annotation_metrics.py  # chunk_boundary P/R/F1（figure_caption 固定 null）
│   ├── runner.py           # 串联 process_single → metrics → report
│   └── report.py           # 聚合 + provenance
├── schemas/
│   ├── document.schema.json       # Stage 1 文档输出
│   ├── manifest.schema.json       # Stage 2 清单
│   ├── annotation.schema.json     # Stage 2 标注
│   └── evaluation-report.schema.json  # Stage 2 报告
├── tests/                  # 单元 + 集成测试
├── samples/
│   ├── README.md           # 告诉你该放什么
│   ├── devset/             # 提交版模板（无真实数据）
│   │   ├── manifest.template.json
│   │   └── annotation.template.json
│   └── private/            # .gitignore；放真实样例（无隐私）
│       └── devset/         # 评测清单与标注（gitignored）
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

---

## 11. Stage 2：评测方法（pilot baseline / incomplete devset）

> 当前开发集仅 1 对 DOCX+PDF，**数字仅反映这对样例上 fallback parser 的表现，
> 不代表项目总体准确率**。完整评测方法见 `docs/evaluation.md`。

### 11.1 跑评测

```bash
.venv/Scripts/python.exe -m evaluation.cli run \
  --manifest samples/private/devset/manifest.json \
  --output outputs/evaluation-pilot-baseline.json \
  --parser fallback \
  --max-chars 800
```

退出码：成功 `0`，清单/报告 Schema 错误 `1`，清单文件不存在 `2`。

### 11.2 校验报告

```bash
.venv/Scripts/python.exe -m evaluation.cli validate-report outputs/evaluation-pilot-baseline.json
```

成功 `[OK]` 退出 0；失败 `[FAIL]` 退出 1；报告不存在 `2`。

### 11.3 指标概览

报告记录每份文档的 13 项自动指标 + 3 项 figure_caption（固定 null）+ 3 项 chunk_boundary P/R/F1（需人工标注）+ 计时。

详细定义见 `docs/evaluation.md` 第 4 节。所有 null 指标都带 `reason` 字段说明未评测原因。

> ⚠️ `text_preservation_equal / text_char_multiset_*` **只**比较 parser 已提取的 elements 与 chunker 生成的 chunks，用于发现**分块阶段**的非空白字符丢失/重复/顺序变化；**不能**证明 PDF/DOCX → elements 的解析完整性。后者由 `silent_drop_count` 部分反映（pilot baseline 中 PDF 该项 = 3）。各项 `1.0` **不等于** "fallback 解析准确率 100%"。
>
> 自 evaluator/report v1.1 起，`text_preservation_*` 改为"删除全部 Unicode 空白后的非空白字符有序序列对比"，不再因 chunker 词内硬切引入的额外空格而误报。旧 v1.0 baseline 的 `text_preservation_*` 与新 v1.1 baseline **不可横向比较**；其他指标语义未变。详见 `docs/evaluation.md` 第 4.1.1 节。

### 11.4 隐私

- 原始报告 JSON 仅写到 `outputs/`（已 gitignored），**不提交 git**
- 私有清单与标注位于 `samples/private/devset/`（已 gitignored）
- 未来若要提交脱敏 Markdown 汇总，必须经用户单独审阅，且不得包含私有路径、SHA-256、annotator 真实身份、文档正文片段
