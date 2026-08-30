# schema_version 版本政策（UDM writer 能力语义）

状态：v1（2026-08-30 批次 6 封口裁决确立"新增 relation type 升 minor"
规则，批次 7 执行时成文；此前规则以沿革记录为准）。

## 1. 基本语义

`schema_version` 描述 **writer（parser 产出）的能力**，不是文档实例的
形状标签。每次 writer 获得新产出能力 → 升 minor 位（0.x.y 的 x）；
`effective_schema_version()` 无条件返回当前能力版本。

## 2. 沿革（已封口，不可改写）

| 版本 | 能力 | 封口批次 |
|---|---|---|
| 0.1.0 | 初始 PDF/DOCX elements | Stage 1 |
| 0.2.0 | source_spans（chunk 字符区间） | Stage 6 批次 2 前 |
| 0.3.0 | locator family（结构化 source_locator） | Stage 6 批次 3 |
| 0.4.0 | relations 数组激活（has_caption） | Stage 6 批次 4 |
| 0.5.0 | 新增 relation type 枚举（table_has_caption） | Stage 6 批次 7 |

## 3. 升版规则

1. **新增产出字段/数组**（结构新面）→ 升 minor。
   例：0.2.0 source_spans、0.4.0 relations 激活。
2. **新增 relation type（扩展 relations[].type 枚举范围）→ 升 minor**
   （2026-08-30 批次 6 封口裁决 Option A）。理由：schema_version 反映
   语义契约而非仅结构——consumers（如 evaluator）需更新逻辑才能完整
   处理新 type；不升版会让 version 失去语义指示作用。先例对齐：批次 4
   的 has_caption 是首个 relation type，0.4.0 表示"激活已存在的
   relations 字段"故该批不另升；此后每新增一个 type 升一次 minor。
3. **既有字段语义收窄/破坏** → 升 major（尚无先例）。
4. 修正性不动产出面的改动（如纯函数收敛、重复实现统一）→ 不升版。
   例：批次 5 表格线性化统一（维持 0.4.0）。

## 4. 读兼容

旧版本永远合法读入：schema 对每个历史版本保留分支；新 type 用
`not.contains` 在旧版本分支精确排除（0.1.0–0.3.0 拒 has_caption、
0.1.0–0.4.0 拒 table_has_caption），保证旧产物可校验、新产物可区分。

## 5. 与 EVALUATOR_VERSION / REPORT_VERSION 的分工

- `schema_version`：UDM writer 产出能力（本文件）。
- `EVALUATOR_VERSION`：评测器能力（能跑哪些 manifest、能消费什么），
  政策见 evaluation/__init__.py 版本历史注释。
- `REPORT_VERSION`：报告结构快照（键集/分节变化才升）。

分工规则（批次 11 裁决补充，2026-08-30）：

- `EVALUATOR_VERSION` 升 minor：新增指标族 / 改匹配算法 / 改降级
  逻辑（例：1.8 figure_caption 消费 relation、1.9 heading_order
  消费 GT）。
- `REPORT_VERSION` 升 minor：改报告结构——新增/删除顶层字段 / 改
  macro 计算范围 / 改报告 schema。指标键扩展不升（报告 schema 的
  per-doc metrics 为开放字典，先例：figure_caption_* 加入时 1.3
  不变，heading_order_* 同）。

