# samples/

测试样例目录。

## 目录布局

| 子目录 | 提交状态 | 用途 |
|---|---|---|
| `samples/devset/` | **提交** | 开发集清单与标注模板（占位符，无真实数据） |
| `samples/private/` | **gitignored** | 真实样例 + 私有开发集清单 + 标注 |
| `samples/private/devset/` | **gitignored** | Stage 2 评测用的清单与标注 |

## 应当放什么

请把以下**无隐私**文件放入 `samples/private/` 子目录（此目录被 `.gitignore` 忽略，不会推送到 GitHub）：

- `samples/private/sample.pdf` —— 任意电子版（非扫描）PDF，例如公开论文、课程笔记导出
- `samples/private/sample.docx` —— 任意 DOCX，例如 Word 笔记

Stage 2 评测还需要（同样 gitignored）：

- `samples/private/devset/manifest.json` —— 开发集清单（参考 `samples/devset/manifest.template.json`）
- `samples/private/devset/annotations/<DOC-ID>.json` —— 人工标注（参考 `samples/devset/annotation.template.json`）

## 为什么不放公开仓库

- 真实样例可能含个人信息或第三方版权内容
- 程序生成的 `outputs/*.json` 可能再现原文，也不应上传
- 评测报告可能含每份文档的 SHA-256、错误原因等可反推信息

## 如果文件不存在

依赖真实样例的集成测试 (`tests/test_pipeline_integration.py`) 会显示 **SKIPPED** 并给出原因，**不会伪造通过**。
评测 CLI 会因找不到 manifest 报错（exit 2），不伪造报告。

## Manifest 路径规则（Stage 2）

- `path` 字段必须是相对项目根目录的**正斜杠**相对路径，例如 `samples/private/sample.docx`
- 拒绝绝对路径与反斜杠
- 解析后路径必须位于项目根目录内
- 详见 `docs/evaluation.md` 第 5 节

## 不允许的做法

- 不要从网上随意下载文件作为样例
- 不要把含个人信息的文件（如申请书）复制到本目录
- 不要硬编码样例的绝对路径到源码或测试中
- 不要把 `samples/private/` 内任何文件提交到 git
