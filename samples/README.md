# samples/

测试样例目录。

## 应当放什么

请把以下两个**无隐私**文件放入 `samples/private/` 子目录（此目录被 `.gitignore` 忽略，不会推送到 GitHub）：

- `samples/private/sample.pdf` —— 任意电子版（非扫描）PDF，例如公开论文、课程笔记导出
- `samples/private/sample.docx` —— 任意 DOCX，例如 Word 笔记

## 为什么不放公开仓库

- 真实样例可能含个人信息或第三方版权内容
- 程序生成的 `outputs/*.json` 可能再现原文，也不应上传

## 如果文件不存在

依赖真实样例的集成测试 (`tests/test_pipeline_integration.py`) 会显示 **SKIPPED** 并给出原因，**不会伪造通过**。

## 不允许的做法

- 不要从网上随意下载文件作为样例
- 不要把含个人信息的文件（如申请书）复制到本目录
- 不要硬编码样例的绝对路径到源码或测试中
