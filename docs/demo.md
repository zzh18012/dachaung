# 最小演示：parse → elements → chunks → relations → schema-valid JSON

静态演示页（R-H，外部评审执行序最后一件）。只展示链路与数字，不含
服务端 / 交互 Web 应用 / 新增运行时依赖。

**演示数据纪律**：两个示例均为评测语料 **dev split** 文档（允许调参面），
不使用 comparison / holdout（protected）样本作展示案例。

---

## 1. 演示链

```
input document (PDF/DOCX)
   │  parse（fallback parser：pdfplumber + python-docx，确定性规则）
   ▼
elements（heading / paragraph / table / caption / image，带 source_locator 溯源）
   │  structural chunker（标题硬边界 + 表格独立 + 长度切分 max_chars）
   ▼
chunks（每个 chunk 携带非空 source_element_ids，可回溯到 element）
   │  relation 抽取（题注绑定 + 显式引用，确定性规则）
   ▼
relations（has_caption / references_table / …，带 deterministic confidence）
   │  JSON Schema 校验（写盘前强制）
   ▼
schema-valid JSON（schema_version 0.6.0）
```

一条命令即可复现（任意无隐私 PDF/DOCX）：

```bash
.venv/Scripts/python.exe -m app.cli parse input.pdf -o out.json --max-chars 1200
.venv/Scripts/python.exe -m app.cli validate out.json   # 独立校验子命令
```

---

## 2. 示例 A：PDF（prod-05-earthlab-manual.pdf，dev split，产品手册）

```bash
.venv/Scripts/python.exe -m app.cli parse prod-05-earthlab-manual.pdf \
  -o demo-prod05.json --max-chars 1200
```

结果（真实运行）：

| 项 | 值 |
|---|---|
| elements | 53（heading 27 / paragraph 15 / image 10 / table 1） |
| chunks | 31 |
| relations | 1（references_table，label="表 1"） |
| warnings / 校验 | 0 / schema-valid（0.6.0） |

表格被文字显式引用时的关系输出（真实产物摘录，内容截断）：

```json
{
  "type": "references_table",
  "from_id": "doc-2898f568f150597b::e0033",
  "to_id": "doc-2898f568f150597b::e0030",
  "metadata": {
    "resolution_method": "ordinal_document_order",
    "confidence": "deterministic",
    "label_source": "ordinal_fallback",
    "label": "表 1"
  }
}
```

---

## 3. 示例 B：DOCX（tech-05-schoolcode.docx，dev split，技术规范）

```bash
.venv/Scripts/python.exe -m app.cli parse tech-05-schoolcode.docx \
  -o demo-tech05.json --max-chars 1200
```

结果（真实运行）：

| 项 | 值 |
|---|---|
| elements | 332（heading 159 / paragraph 148 / table 12 / caption 12 / image 1） |
| chunks | 190 |
| relations | 19（references_table，逐表绑定 caption label 如"表2"） |
| warnings / 校验 | 0 / schema-valid（0.6.0） |

### JSON 片段（真实产物摘录，内容截断）

标题 element（DOCX locator = structural_index，无页码——如实反映 DOCX
无稳定页码的事实）：

```json
{
  "element_id": "doc-f3cc68f09892e2ed::e0061",
  "type": "heading",
  "content": "1.0.1  为使中小学校项目建设满足国家规定的办学标准，保障在校师生人身健康、…",
  "source_locator": {"family": "structural_index", "paragraph_index": 59, "section": 0},
  "confidence": 0.95
}
```

正文段落 → 表格的显式引用关系（"限值应符合表2.2.4的规定。" → 目标表）：

```json
{
  "relation": {
    "type": "references_table",
    "from_id": "doc-f3cc68f09892e2ed::e0100",
    "to_id": "doc-f3cc68f09892e2ed::e0096",
    "metadata": {"resolution_method": "ordinal_document_order",
                  "confidence": "deterministic",
                  "label_source": "caption_label", "label": "表2"}
  },
  "from": {"type": "paragraph", "content": "限值应符合表2.2.4的规定。",
            "source_locator": {"family": "structural_index",
                                "paragraph_index": 97, "section": 0}},
  "to": {"type": "table", "content": "| 类别 | 设计工作年限（年） |\n| --- |…",
          "source_locator": {"family": "structural_index",
                              "table_index": 1, "section": 0}}
}
```

chunk（独立表格块，溯源到源 element，不丢不重）：

```json
{
  "chunk_id": "doc-f3cc68f09892e2ed::c0001",
  "text": "| 中华人民共和国住房和城乡建设部 | 联合发布 |\n| --- |…",
  "source_element_ids": ["doc-f3cc68f09892e2ed::e0021"],
  "metadata": {"strategy": "isolated_table", "max_chars": 1200, "char_count": 62}
}
```

---

## 4. 结题指标表（摘要，详见 main README §0 与评测台账）

| 面 | 指标 | 值 |
|---|---|---|
| 结构（comparison 门面，24 core docs） | unit_alignment / coverage / nontext / boundary_err | 0.8297 / 0.7635 / 0.7004 / 0.7378 |
| ARI（dev 14，vs 人工标注） | 系统 / B1 / B2 / oracle 上界 | **0.3345** / 0.2658 / 0.2621 / 0.4159（目标 0.75 NOT MET，粒度失配结构性） |
| 关系（fixed-anchor，acad-03，20 edges） | P / R / F1 | 1.0 / 0.35 / 0.5185 |
| 解析 | 成功率 / schema 校验 | 24/24 / 1.0 |

## 5. Limitations / scope note

- 全程确定性规则：no OCR、no probabilistic matching、no learned layout
  model（扫描件 PDF 不做文字识别，按 warning 如实报告）。
- ARI 目标 0.75 在冻结分块契约（max_chars≤2000）下结构性不可达
  （oracle 上界 0.4159）；系统达天花板 80.4%，差距主体为金标粒度与
  契约的失配，非实现缺陷。扩展 N 粒度诊断为 diagnostic 附录，非生产建议。
- 关系评测范围 = fixed-anchor（acad-03，20 gold edges），不宣称
  24 篇 corpus-wide；relation recall 0.35 为已知限制。
- booktabs 表格文本检测缺口、acad-06 图内小表漏检等已知限制见
  main README §0.6。
